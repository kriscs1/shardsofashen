"""The central server: accounts, tickets into a game server, the remote servers list."""
import asyncio
import json
import os
import re
import socket
import time

import aiohttp
import pytest
from aiohttp import web

from central.app import make_central
from central.store import CentralStore
from server.app import make_app, GAME
from tests.test_server import ROOT, come_in, device_of, replies


SIGNUP = {"password": "longpassword", "email": "player@example.com"}


@pytest.fixture
def confirmed(monkeypatch):
    """Sign-ups whose email counts at once (each its own): for the tests about what comes after."""
    monkeypatch.setattr(CentralStore, "set_pending_email",
                        lambda self, name, email: self.set_email(name, name.lower() + "@example.com"))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def run(app):
    runner = web.AppRunner(app)
    await runner.setup()
    port = free_port()
    await web.TCPSite(runner, "127.0.0.1", port).start()
    return runner, port


async def post(http, url, body):
    async with http.post(url, json=body) as r:
        return await r.json()


async def ticket_in(http, url, ticket, name="Wanderer", device="a phone"):
    """In by a ticket: one of the account's characters here, or a new one called name."""
    ws, m = await come_in(http, url, device_of(device), ticket=ticket)
    if m["t"] == "login_fail":
        return ws, m
    mine = [c["name"] for c in m["list"]]
    await ws.send_json({"t": "play" if name in mine else "create", "name": name})
    return ws, await replies(ws, ("welcome", "login_fail"))


def test_every_self_hosted_template_offers_the_central_server():
    """A setting a template leaves out can't be turned on there (Unraid's had none of them)."""
    for name in ("unraid/shards-of-ashen.xml", "docker-compose.yml", "docker-compose.server.yml",
                 "docker-compose.cloud.yml"):
        with open(os.path.join(ROOT, "deploy", name), encoding="utf-8") as f:
            text = f.read()
        for var in ("DS_CENTRAL", "DS_PUBLIC", "DS_PUBLIC_URL", "DS_TRUST_PROXY"):
            assert re.search(r"\b%s\b" % var, text), (name, var)


def link_in(text):
    return re.search(r"/confirm\?code=(\w+)", text).group(1)


async def until_mail(mail, n=1):
    for _ in range(200):
        if len(mail.SENT) >= n:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("no email: %r" % mail.SENT)


def test_an_email_counts_only_once_its_owner_confirms_it(tmp_path, monkeypatch):
    """Given at sign-up or later, an address gets a link; opening it does nothing (a mail scanner opens links), its
    button confirms it. Till then no code goes to it and the one before it still counts."""
    from central import mail
    from central import store as central_store
    monkeypatch.setenv("DS_SMTP_HOST", "test")
    mail.SENT.clear()

    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        db = capp["central"].store
        try:
            async with aiohttp.ClientSession() as http:
                async def forgot(who):
                    mail.SENT.clear()
                    r = await post(http, c + "/api/forgot", {"who": who})
                    return r["ok"] and [m[0] for m in mail.SENT]

                async def confirm(code):
                    async with http.post(c + "/confirm", data={"code": code}) as r:
                        return await r.text()

                r = await post(http, c + "/api/register", {"name": "Ann", **SIGNUP,
                                                           "email": "ann@example.com"})
                assert r["confirm"]
                token = r["token"]
                await until_mail(mail)
                first = link_in(mail.SENT[0][2])
                me = await post(http, c + "/api/account", {"token": token})
                assert me["email"] == "" and me["pending"] == "ann@example.com"
                assert await forgot("Ann") == [] and await forgot("ann@example.com") == []     # (not till it's confirmed)

                page = await (await http.get(c + "/confirm?code=" + first)).text()
                assert "ann@example.com" in page and "<button>" in page
                assert (await post(http, c + "/api/account", {"token": token}))["email"] == ""  # (opening it isn't enough)
                assert "Email confirmed" in await confirm(first)
                me = await post(http, c + "/api/account", {"token": token})
                assert me["email"] == "ann@example.com" and me["pending"] == ""
                assert await forgot("Ann") == ["ann@example.com"]
                assert "run out" in await confirm(first)                                       # (once)
                assert "run out" in await (await http.get(c + "/confirm?code=" + first)).text()
                assert "run out" in await (await http.get(c + "/confirm")).text()              # (no code: no match on none)

                mail.SENT.clear()                                                              # (a new address)
                r = await post(http, c + "/api/email", {"token": token, "email": "new@example.com"})
                assert r["email"] == "ann@example.com" and r["pending"] == "new@example.com"
                old_link = link_in(mail.SENT[0][2])
                assert mail.SENT[0][0] == "new@example.com"
                assert await forgot("Ann") == ["ann@example.com"]                              # (the old one, till then)
                mail.SENT.clear()
                assert (await post(http, c + "/api/email/again", {"token": token}))["ok"]
                new_link = link_in(mail.SENT[0][2])
                assert "run out" in await confirm(old_link)                                    # (the newer link only)

                other = await post(http, c + "/api/register", {"name": "Bob", **SIGNUP,
                                                               "email": "bob@example.com"})
                refused = await post(http, c + "/api/email", {"token": other["token"], "email": "ann@example.com"})
                assert not refused["ok"]                                                       # (confirmed: Ann's)
                await post(http, c + "/api/email", {"token": other["token"], "email": "new@example.com"})
                bobs = link_in(mail.SENT[-1][2])
                assert "Email confirmed" in await confirm(new_link)
                assert "on another account" in await confirm(bobs)                             # (Ann got there first)
                assert (await post(http, c + "/api/account", {"token": other["token"]}))["email"] == ""

                r = await post(http, c + "/api/email", {"token": token, "email": ""})          # (it can't be taken off)
                assert not r["ok"] and "needs an email" in r["text"]
                assert (await post(http, c + "/api/account", {"token": token}))["email"] == "new@example.com"

                mail.SENT.clear()                                                              # (no flooding an address)
                capp["central"].confirms = {}                                                  # (a new day's count)
                await post(http, c + "/api/email", {"token": other["token"], "email": "flood@example.com"})
                tries = [await post(http, c + "/api/email/again", {"token": other["token"]}) for _ in range(8)]
                assert len([m for m in mail.SENT if m[0] == "flood@example.com"]) == 5
                assert not tries[-1]["ok"] and "enough" in tries[-1]["text"]

                await post(http, c + "/api/email", {"token": token, "email": "<b>x</b>@example.com"})
                code = link_in(mail.SENT[-1][2])
                page = await (await http.get(c + "/confirm?code=" + code)).text()
                assert "<b>x</b>" not in page and "&lt;b&gt;" in page                          # (written safely)

                db.db.execute("UPDATE mailchecks SET made = ?", (time.time() - (central_store.CONFIRM_DAYS + 1) * 86400,))
                assert "run out" in await confirm(code)                                        # (too old)
                db.db.execute("UPDATE mailchecks SET made = ?", (time.time() - (central_store.UNCONFIRMED_DAYS + 1) * 86400,))
                db.prune()
                assert db.pending_email("Ann") == ""                                           # (forgotten)
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_no_recovery_codes_and_every_account_has_an_email(tmp_path, monkeypatch):
    """A forgotten password goes only by email. An account from before has its old code wiped; with no email it's asked
    for one, and can't join a game till it's given."""
    path = str(tmp_path / "central.db")
    old = CentralStore(path)
    old.create_account("Oldie", "not-a-real-hash")
    old.db.execute("UPDATE accounts SET recover = 'a-saved-code-hash' WHERE name = 'Oldie'")
    old.db.close()

    async def go():
        capp = make_central(path)
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        store = capp["central"].store
        try:
            async with aiohttp.ClientSession() as http:
                assert store.account("Oldie")[2] == ""                                         # (wiped)
                assert (await http.post(c + "/api/recovery", json={"token": "x"})).status == 404
                r = await post(http, c + "/api/register", {"name": "Nomail", "password": "longpassword"})
                assert not r["ok"] and "needs an email" in r["text"]
                r = await post(http, c + "/api/register", {"name": "Nomail", "password": "longpassword", "email": "nope"})
                assert not r["ok"] and "doesn't look like" in r["text"]

                r = await post(http, c + "/api/register", {"name": "Newbie", **SIGNUP})
                assert r["ok"] and r["confirm"] and "recovery" not in r
                assert (await post(http, c + "/api/me", {"token": r["token"]}))["needs_email"] is False
                m = await post(http, c + "/api/ticket", {"token": r["token"], "server": "abc"})
                assert not m["ok"] and m["refused"] and "Confirm your email" in m["text"]      # (not till it's confirmed)
                store.set_email("Newbie", "player@example.com")
                assert (await post(http, c + "/api/ticket", {"token": r["token"], "server": "abc"}))["ok"]

                token = store.new_token("Oldie")
                assert (await post(http, c + "/api/me", {"token": token}))["needs_email"] is True
                m = await post(http, c + "/api/ticket", {"token": token, "server": "abc"})
                assert not m["ok"] and m["refused"] and "needs an email" in m["text"]
                assert (await post(http, c + "/api/email", {"token": token, "email": "old@example.com"}))["ok"]
                assert (await post(http, c + "/api/me", {"token": token}))["needs_email"] is False
                m = await post(http, c + "/api/ticket", {"token": token, "server": "abc"})
                assert not m["ok"] and "Confirm your email" in m["text"]
                store.set_email("Oldie", "old@example.com")
                assert (await post(http, c + "/api/ticket", {"token": token, "server": "abc"}))["ok"]

                m = await post(http, c + "/api/reset", {"name": "Newbie", "code": "AAAA-BBBB", "password": "newpassword1"})
                assert not m["ok"]                                                             # (no code of any other kind)
                m = await post(http, c + "/api/forgot", {"who": "Newbie"})
                assert not m["ok"] and "recovery" not in m["text"]                             # (no email to send: says so)
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_a_bans_reason_shows_where_they_have_proved_who_they_are(tmp_path, monkeypatch):
    """Signing in, or a ticket, says why. Anyone can ask whether a name is banned, so that never says why."""
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")
        store = crunner.app["central"].store
        try:
            async with aiohttp.ClientSession() as http:
                tok = (await post(http, central + "/api/register", {"name": "Rogue", **SIGNUP}))["token"]
                store.set_banned("Rogue", "cheating at cards")
                m = await post(http, central + "/api/login", {"name": "Rogue", "password": "longpassword"})
                assert "cheating at cards" in m["text"]
                m = await post(http, central + "/api/ticket", {"token": tok, "server": "abc"})
                assert not m["ok"] and m["refused"] and "cheating at cards" in m["text"]
                m = await post(http, central + "/api/game/standing", {"name": "Rogue"})
                assert m["banned"] is True and "cheating" not in json.dumps(m)
        finally:
            await crunner.cleanup()
    asyncio.run(go())


def test_an_admin_deletes_an_account_keeping_its_name_or_freeing_it(tmp_path, monkeypatch, confirmed):
    """Either way all that's theirs goes and they're turned away from a game. Delete keeps the name back; the other
    frees it. An admin can't be deleted (a name in DS_CENTRAL_ADMINS left free would make whoever took it an admin)."""
    async def go():
        monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")
        capp = make_central(str(tmp_path / "central.db"))
        crunner, cport = await run(capp)
        c = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", c)
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5)
        grunner, gport = await run(gapp)
        game, url = gapp[GAME], "ws://127.0.0.1:%d/ws" % gport
        store = capp["central"].store
        try:
            async with aiohttp.ClientSession() as http:
                boss = (await post(http, c + "/api/register", {"name": "Boss", **SIGNUP,
                                                               "claim": capp["central"].claims.get("boss", "")}))["token"]
                pal = (await post(http, c + "/api/register", {"name": "Pal", **SIGNUP}))["token"]

                async def signup(name):
                    capp["central"].signups.clear()
                    return (await post(http, c + "/api/register", {"name": name, **SIGNUP,
                                                                   "email": name + "@example.com"}))["token"]

                async def gone_from_everywhere(name, tok):
                    assert not (await post(http, c + "/api/me", {"token": tok}))["ok"]
                    assert not (await post(http, c + "/api/ticket", {"token": tok, "server": "abc"}))["ok"]
                    assert (await post(http, c + "/api/game/standing", {"name": name}))["banned"] is True
                    assert (await post(http, c + "/api/friends", {"token": pal}))["friends"] == []
                    for table in ("tokens", "tickets", "grants", "mailcodes", "mailchecks", "playing"):
                        assert not store.db.execute("SELECT 1 FROM %s WHERE name = ?" % table, (name,)).fetchone()
                    assert not store.db.execute("SELECT 1 FROM friends WHERE who = ? OR whom = ?", (name, name)).fetchone()

                # (not for anyone but an admin, and not an admin)
                assert not (await post(http, c + "/api/admin/delete", {"token": pal, "name": "Boss"}))["ok"]
                m = await post(http, c + "/api/admin/erase", {"token": boss, "name": "Boss"})
                assert not m["ok"] and "admin" in m["text"] and store.account("Boss")
                await post(http, c + "/api/admin/make_admin", {"token": boss, "name": "Pal", "on": True})
                assert not (await post(http, c + "/api/admin/delete", {"token": boss, "name": "Pal"}))["ok"]
                await post(http, c + "/api/admin/make_admin", {"token": boss, "name": "Pal", "on": False})

                # (Delete: in play with a key, and hosting for friends)
                tok = await signup("Kept")
                await post(http, c + "/api/friend", {"token": tok, "name": "Pal"})
                await post(http, c + "/api/friend", {"token": pal, "name": "Kept"})
                assert (await post(http, c + "/api/friends", {"token": pal}))["friends"] == ["Kept"]
                ticket = (await post(http, c + "/api/ticket", {"token": tok, "server": game.server_id()}))["ticket"]
                ws, m = await ticket_in(http, url, ticket, name="Keeper", device="a laptop")
                assert m["t"] == "welcome"
                grant = store.new_grant("Kept", "hostgame1")
                host = await http.ws_connect("http://127.0.0.1:%d/api/relay?grant=%s&key=hostgame1" % (cport, grant))
                await asyncio.sleep(0.1)
                assert "hostgame1" in capp["central"].relays.tunnels
                count = store.count_accounts()

                assert (await post(http, c + "/api/admin/delete", {"token": boss, "name": "Kept"}))["ok"]
                await gone_from_everywhere("Kept", tok)
                await host.receive()
                assert host.closed and "hostgame1" not in capp["central"].relays.tunnels
                await game.keep_friends()                                       # (the minute's check, in play)
                assert (await replies(ws, ("kicked",)))["t"] == "kicked"
                await ws.close()
                await asyncio.sleep(0.2)
                back, m = await come_in(http, url, device_of("a laptop"))       # (straight back: no ticket)
                assert m["t"] == "login_fail"
                await back.close()

                acct = store.account("Kept")
                assert acct[1:5] == ("", "", "", "") and not acct[5] and acct[6]    # (the name, and nothing else of theirs)
                assert store.count_accounts() == count - 1
                m = await post(http, c + "/api/login", {"name": "Kept", "password": "longpassword"})
                assert not m["ok"] and "deleted" in m["text"]
                m = await post(http, c + "/api/reset", {"name": "Kept", "code": "", "password": "anotherpassword"})
                assert not m["ok"]
                capp["central"].signups.clear()
                m = await post(http, c + "/api/register", {"name": "kept", **SIGNUP})
                assert not m["ok"] and "taken" in m["text"]                     # (nor by another case of it)
                assert not (await post(http, c + "/api/friend", {"token": pal, "name": "Kept"}))["ok"]
                assert not (await post(http, c + "/api/admin/ban", {"token": boss, "name": "Kept"}))["ok"]
                assert not (await post(http, c + "/api/admin/make_admin", {"token": boss, "name": "Kept", "on": True}))["ok"]
                found = (await post(http, c + "/api/admin/accounts", {"token": boss, "q": "Kept"}))["accounts"]
                assert found[0]["deleted"] and not found[0]["email"]

                # (and a name kept back can be freed after)
                assert (await post(http, c + "/api/admin/erase", {"token": boss, "name": "Kept"}))["ok"]
                assert store.account("Kept") is None

                # (Delete and free the name: another may take it, and the email)
                tok = await signup("Freed")
                store.set_email("Freed", "Freed@example.com")
                assert (await post(http, c + "/api/admin/erase", {"token": boss, "name": "Freed"}))["ok"]
                await gone_from_everywhere("Freed", tok)
                assert store.account("Freed") is None and store.account_by_email("Freed@example.com") is None
                m = await post(http, c + "/api/login", {"name": "Freed", "password": "longpassword"})
                assert not m["ok"] and "deleted" not in m["text"]
                new = await signup("Freed")
                assert (await post(http, c + "/api/me", {"token": new}))["name"] == "Freed"
                assert (await post(http, c + "/api/game/standing", {"name": "Freed"}))["banned"] is False
        finally:
            await grunner.cleanup()
            await crunner.cleanup()
    asyncio.run(go())


def test_a_new_account_with_an_email_is_welcomed(tmp_path, monkeypatch):
    """A welcome with its link for whoever gives an address (never their password or recovery code), and a mail
    service's trouble doesn't stop the sign-up. Email that goes has what mail services want of it."""
    from central import mail

    async def go():
        monkeypatch.setenv("DS_SMTP_HOST", "test")
        mail.SENT.clear()
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        try:
            async with aiohttp.ClientSession() as http:
                r = await post(http, central + "/api/register", {"name": "Quiet", "password": "longpassword"})
                assert not r["ok"] and "needs an email" in r["text"]            # (one's required)
                r = await post(http, central + "/api/register", {"name": "Hello", **SIGNUP,
                                                                 "email": "hello@example.com"})
                assert r["ok"]
                await asyncio.sleep(0.2)
                assert [m[0] for m in mail.SENT] == ["hello@example.com"]
                to, subject, text = mail.SENT[0]
                assert "confirm" in subject and "Welcome" in text and "Hello" in text and link_in(text)
                assert "longpassword" not in text and "recovery" not in r

                def broken(*args):
                    raise OSError("the mail service is away")
                monkeypatch.setattr(mail, "send", broken)
                r = await post(http, central + "/api/register", {"name": "Still", **SIGNUP,
                                                                 "email": "still@example.com"})
                assert r["ok"] and r["token"]
                await asyncio.sleep(0.2)
        finally:
            await crunner.cleanup()
    asyncio.run(go())
    monkeypatch.setenv("DS_SMTP_FROM", "Shards of Ashen <shardsofashen@hallisium.com>")
    msg = mail.message("you@example.com", "A subject", "Words.\n")
    assert msg["From"] == "Shards of Ashen <shardsofashen@hallisium.com>" and msg["Date"]
    assert msg["Message-ID"].endswith("@hallisium.com>")


def test_a_central_ban_reaches_those_who_come_straight_back(tmp_path, monkeypatch, confirmed):
    """A device that came in by its account comes back with no ticket: still them, till the central server bans the
    account (and that turns away who's playing, at the next minute's check). The central server away isn't a ban."""
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5)
        grunner, gport = await run(gapp)
        game = gapp[GAME]
        url = "ws://127.0.0.1:%d/ws" % gport
        try:
            async with aiohttp.ClientSession() as http:
                boss = (await post(http, central + "/api/register", {"name": "Boss", **SIGNUP}))["token"]
                tok = (await post(http, central + "/api/register", {"name": "Rogue", **SIGNUP}))["token"]

                async def ticket():
                    return (await post(http, central + "/api/ticket", {"token": tok, "server": game.server_id()}))["ticket"]
                ws, m = await ticket_in(http, url, await ticket(), name="Roguey", device="a laptop")
                assert m["t"] == "welcome"
                await ws.close()
                await asyncio.sleep(0.2)

                ws, m = await come_in(http, url, device_of("a laptop"))         # (straight back: no ticket)
                assert m["t"] == "characters" and m["account"] == "Rogue"
                await ws.send_json({"t": "play", "name": "Roguey"})
                assert (await replies(ws, ("welcome", "login_fail")))["t"] == "welcome"
                late = await ticket()                                           # (made before the ban, used after)

                await post(http, central + "/api/admin/ban", {"token": boss, "name": "Rogue", "why": "testing"})
                await game.keep_friends()                                       # (the minute's check, in play)
                assert (await replies(ws, ("kicked",)))["reason"] == "Your Shards account is banned."
                await ws.close()
                await asyncio.sleep(0.2)

                back, m = await come_in(http, url, device_of("a laptop"))
                assert m["t"] == "login_fail" and "banned" in m["reason"]
                await back.close()
                new, m = await come_in(http, url, device_of("a new phone"), ticket=late)
                assert m["t"] != "characters" or m["account"] != "Rogue"        # (the old ticket's no way in either)
                await new.close()

                monkeypatch.setenv("DS_CENTRAL", "http://127.0.0.1:%d" % free_port())   # (it's away: no word of a ban)
                ws, m = await come_in(http, url, device_of("a laptop"))
                assert m["t"] == "characters" and m["account"] == "Rogue"
                await ws.close()
        finally:
            await grunner.cleanup()
            await crunner.cleanup()
    asyncio.run(go())


def test_the_central_server_says_its_version_and_who_is_behind(tmp_path, monkeypatch):
    """/health says its version; the admin page marks a server older than it, and only one it can tell is older."""
    async def go():
        monkeypatch.setenv("DS_BUILD", "500")
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")
        try:
            async with aiohttp.ClientSession() as http:
                assert (await (await http.get(central + "/health")).json())["version"].endswith(".500")
                boss = (await post(http, central + "/api/register", {"name": "Boss", **SIGNUP}))["token"]
                for name, version in (("Old", "1.0.499"), ("Same", "1.0.500"), ("New", "1.0.501"), ("Dev", "1.0-dev"),
                                      ("Quiet", "")):
                    r = await post(http, central + "/api/announce", {"name": name, "url": "https://%s.example.com" % name,
                                                                     "port": 8484, "max": 5, "version": version})
                    assert r["ok"]
                got = await post(http, central + "/api/admin/servers", {"token": boss})
                assert got["version"].endswith(".500")
                assert {s["name"]: s["behind"] for s in got["servers"]} == {
                    "Old": True, "Same": False, "New": False, "Dev": False, "Quiet": False}
        finally:
            await crunner.cleanup()
    asyncio.run(go())


def test_one_account_for_every_game_and_the_remote_list(tmp_path, monkeypatch, confirmed):
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        monkeypatch.setenv("DS_PUBLIC", "1")
        monkeypatch.setenv("DS_PUBLIC_URL", "https://play.example.com")
        monkeypatch.setenv("DS_CENTRAL_ADMINS", "Wanderer")
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Kris's World")
        grunner, gport = await run(gapp)
        game = gapp[GAME]
        wsurl = "ws://127.0.0.1:%d/ws" % gport
        try:
            async with aiohttp.ClientSession() as http:
                r = await post(http, central + "/api/register", {"name": "Wanderer", **SIGNUP})
                assert r["ok"] and r["token"]
                token = r["token"]
                for _ in range(40):                                     # (it announces itself as it starts)
                    await asyncio.sleep(0.1)
                    waiting = (await post(http, central + "/api/admin/servers", {"token": token}))["servers"]
                    if waiting:
                        break
                assert waiting and waiting[0]["key"] == game.server_id() and not waiting[0]["approved"]
                assert await (await http.get(central + "/api/servers")).json() == []    # (not listed till approved)
                assert (await post(http, central + "/api/admin/approve", {"token": token, "key": game.server_id(),
                                                                          "on": True}))["ok"]
                listed = await (await http.get(central + "/api/servers")).json()
                assert listed and listed[0]["key"] == game.server_id() and listed[0]["name"] == "Kris's World"
                assert listed[0]["url"] == "https://play.example.com"
                info = await (await http.get("http://127.0.0.1:%d/api/info" % gport)).json()
                assert info["id"] == game.server_id()

                assert (await post(http, central + "/api/me", {"token": token}))["name"] == "Wanderer"
                here = "https://play.example.com"
                relayed = await post(http, central + "/api/ticket", {"token": token, "server": game.server_id(),
                                                                     "url": "http://evil.example:8484"})
                assert not relayed["ok"]            # (another game giving this one's id: no ticket to pass on)
                t = await post(http, central + "/api/ticket", {"token": token, "server": game.server_id(),
                                                               "url": here})
                ws, m = await ticket_in(http, wsurl, t["ticket"])
                assert m["t"] == "welcome" and m["name"] == "Wanderer" and m["account"] == "Wanderer"
                await ws.close()
                ws, m = await ticket_in(http, wsurl, t["ticket"], device="another")
                assert m["t"] == "login_fail"                               # (a ticket's good once)
                await ws.close()
                other = await post(http, central + "/api/ticket", {"token": token, "server": "0123456789abcdef"})
                ws, m = await ticket_in(http, wsurl, other["ticket"], device="another")
                assert m["t"] == "login_fail"                               # (made out to another server)
                await ws.close()

                bad = await post(http, central + "/api/login", {"name": "Wanderer", "password": "wrong"})
                assert not bad["ok"]
                hello = await (await http.get(central + "/api/hello")).json()
                assert hello["ok"] and hello["ad"]["text"] and hello["servers"] == 1
        finally:
            await grunner.cleanup()
            await crunner.cleanup()
        async with aiohttp.ClientSession() as http:                   # (stopped: it said goodbye)
            pass
    asyncio.run(go())


def test_every_version_has_the_same_start_screen():
    """The Android app's start screen is web/home's (tools/sync_home.py copies it)."""
    import os
    for f in ("index.html", "config.js"):
        a = open(os.path.join(ROOT, "web", "home", f), "rb").read()
        b = open(os.path.join(ROOT, "android", "app", "src", "main", "assets", "home", f), "rb").read()
        assert a == b, "run tools/sync_home.py"


def test_making_an_account_asks_for_the_privacy_policy():
    """The sign-up can't go ahead without its tick, and the policy opens over the form, whatever's typed kept."""
    import os
    import re
    page = open(os.path.join(ROOT, "web", "home", "index.html"), encoding="utf-8").read()
    form = re.search(r'<form id="form-new".*?</form>', page, re.S).group(0)
    assert '<input id="new-agree" type="checkbox" required>' in form and "privacy-link" in form
    assert form.index("new-agree") < form.index('type="submit"')
    assert "<iframe" in page and 'app.play(CENTRAL + "/privacy")' not in page


def test_email_reset_privacy_admin_and_ads(tmp_path, monkeypatch):
    """A forgotten password by an emailed code; the privacy policy; the admin page's accounts, bans and ads."""
    from central import mail
    monkeypatch.setenv("DS_SMTP_HOST", "test")
    monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")
    monkeypatch.setenv("DS_ADSENSE_CLIENT", "ca-pub-1234567890")
    monkeypatch.setenv("DS_ADMOB_APP", "ca-app-pub-1234567890~5555")
    mail.SENT.clear()

    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        try:
            async with aiohttp.ClientSession() as http:
                assert not (await post(http, c + "/api/register", {"name": "Mail", **SIGNUP,
                                                                    "email": "not an email"}))["ok"]
                r = await post(http, c + "/api/register", {"name": "Mail", **SIGNUP,
                                                            "email": "mail@example.com"})
                assert r["ok"]
                await until_mail(mail)                  # (the link goes to one side: past it, to the code)
                async with http.post(c + "/confirm", data={"code": link_in(mail.SENT[0][2])}) as done:
                    assert "Email confirmed" in await done.text()
                mail.SENT.clear()
                r = await post(http, c + "/api/forgot", {"who": "mail@example.com"})
                assert r["ok"] and len(mail.SENT) == 1 and mail.SENT[0][0] == "mail@example.com"
                code = [w for w in mail.SENT[0][2].split() if "-" in w and len(w) == 9][0]
                assert not (await post(http, c + "/api/reset", {"name": "Mail", "code": "AAAA-BBBB",
                                                                 "password": "newpassword1"}))["ok"]
                r = await post(http, c + "/api/reset", {"name": "mail@example.com", "code": code,
                                                         "password": "newpassword1"})
                assert r["ok"] and r["name"] == "Mail" and "recovery" not in r
                assert not (await post(http, c + "/api/reset", {"name": "Mail", "code": code,
                                                                 "password": "newpassword2"}))["ok"]   # (used up)
                assert (await post(http, c + "/api/login", {"name": "Mail", "password": "newpassword1"}))["ok"]

                page = await (await http.get(c + "/privacy")).text()
                assert "Privacy policy" in page and "Google AdSense" in page and "server you made them on" in page
                assert "pub-1234567890" in await (await http.get(c + "/ads.txt")).text()
                assert "Google AdMob" in page
                lines = (await (await http.get(c + "/app-ads.txt")).text()).splitlines()
                assert lines == ["google.com, pub-1234567890, DIRECT, f08c47fec0942fa0"]    # (one publisher, once)
                hello = await (await http.get(c + "/api/hello")).json()
                assert hello["adsense"]["client"] == "ca-pub-1234567890" and hello["mail"]
                assert "admin" in (await (await http.get(c + "/admin")).text()).lower()

                squat = await post(http, c + "/api/register", {"name": "Boss", **SIGNUP})
                assert not squat["ok"] and squat["claim"]       # (an admin's name: only with the code from the log)
                boss = (await post(http, c + "/api/register", {"name": "Boss", **SIGNUP,
                                                               "claim": capp["central"].claims["boss"]}))["token"]
                mine = (await post(http, c + "/api/login", {"name": "Mail", "password": "newpassword1"}))["token"]
                assert not (await post(http, c + "/api/admin/stats", {"token": mine}))["ok"]    # (not an admin)
                found = (await post(http, c + "/api/admin/accounts", {"token": boss, "q": "mail"}))["accounts"]
                assert [a["name"] for a in found] == ["Mail"]
                await post(http, c + "/api/admin/ban", {"token": boss, "name": "Mail", "why": "testing"})
                m = await post(http, c + "/api/login", {"name": "Mail", "password": "newpassword1"})
                assert not m["ok"] and "banned" in m["text"]
                await post(http, c + "/api/admin/ads", {"token": boss, "ads": [{"text": "Buy shards", "link": ""}]})
                assert (await (await http.get(c + "/api/hello")).json())["ad"]["text"] == "Buy shards"
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_the_admin_code_stays_the_same_across_restarts(tmp_path, monkeypatch):
    """The admin code in the log is kept: a restart or an update doesn't make the one given out wrong."""
    from central.app import Central
    monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")
    db = str(tmp_path / "central.db")
    first = Central(db).claims["boss"]
    assert first and Central(db).claims["boss"] == first


def test_a_listed_game_is_approved_again_when_it_changes_and_calls_are_limited(tmp_path):
    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        store = capp["central"].store
        try:
            async with aiohttp.ClientSession() as http:
                r = await post(http, c + "/api/announce", {"name": "Good Game", "url": "https://good.example",
                                                            "online": "lots", "max": 5, "port": "x"})
                assert r["ok"]                                           # (a bad number: not a fault)
                store.set_approved(r["key"], True)
                same = {"key": r["key"], "secret": r["secret"], "name": "Good Game", "url": "https://good.example",
                        "online": 99999, "max": 5}
                assert (await post(http, c + "/api/announce", same))["approved"]
                listed = await (await http.get(c + "/api/servers")).json()
                assert listed[0]["online"] <= listed[0]["max"]           # (no 99999 of 5)
                moved = dict(same, name="FREE GOLD", url="https://phish.example")
                assert not (await post(http, c + "/api/announce", moved))["approved"]   # (approved again first)
                said = [await post(http, c + "/api/announce", {"name": "Spam %d" % k, "url": "https://x.example"})
                        for k in range(40)]
                assert not all(x["ok"] for x in said)                   # (not hundreds of rows from one address)
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_friends_are_by_account_in_every_game(tmp_path, monkeypatch, confirmed):
    """Two Shards accounts: one asks, the other accepts (on the start screen, or in a game by right-click or the
    journal), and they're friends in every game, any character of theirs; a game says where they're playing; the
    world's old friends of a character move over to its account; a homestead lets an account's friends in."""
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Kris's World")
        grunner, gport = await run(gapp)
        game = gapp[GAME]
        wsurl = "ws://127.0.0.1:%d/ws" % gport
        try:
            async with aiohttp.ClientSession() as http:
                tok = {}
                for n in ("Alpha", "Beta", "Gamma"):
                    tok[n] = (await post(http, central + "/api/register", {"name": n, **SIGNUP}))["token"]
                r = await post(http, central + "/api/friend", {"token": tok["Alpha"], "name": "nobody"})
                assert not r["ok"]
                r = await post(http, central + "/api/friend", {"token": tok["Alpha"], "name": "gamma"})
                assert r["done"] == "asked" and r["asked"] == ["Gamma"]
                r = await post(http, central + "/api/friends", {"token": tok["Gamma"]})
                assert r["asking"] == ["Alpha"] and r["friends"] == []
                r = await post(http, central + "/api/friend", {"token": tok["Gamma"], "name": "Alpha"})
                assert r["done"] == "friends" and r["friends"] == ["Alpha"]

                async def come(account, char):
                    t = await post(http, central + "/api/ticket", {"token": tok[account], "server": game.server_id()})
                    return await ticket_in(http, wsurl, t["ticket"], char, device=account)
                game.world.together.friends["Bee"] = ["Ace"]          # (the world's own list, from before)
                game.world.together.accounts["Ace"] = "Alpha"
                a, m = await come("Alpha", "Ace")
                assert m["t"] == "welcome"
                b, m = await come("Beta", "Bee")
                await asyncio.sleep(1.0)
                sa, sb = game.world.sessions["Ace"], game.world.sessions["Bee"]
                assert sb.central_friends["asked"] == ["Alpha"]           # (Bee's old friend Ace: asked by account)
                assert "Bee" not in game.world.together.friends or not game.world.together.friends["Bee"]
                game.world.tick(0.05, now=game.world.now + 50)
                await game.friends_now(sa)
                assert sa.central_friends["asking"] == ["Beta"] and sa.central_friends["friends"] == ["Gamma"]
                rows = sa.friends_rows()
                assert rows[0]["asks"] and rows[0]["account"] == "Beta"
                sa.add_friend_named("Beta", True)                         # (the journal's Accept)
                await asyncio.sleep(1.0)
                assert "Beta" in sa.central_friends["friends"] and "Bee" in sa.friend_names()
                assert "Ace" in sb.friend_names()
                row = next(r for r in sa.friends_rows() if r.get("char") == "Bee")
                assert row["name"] == "Bee (Beta)" and row["on"]
                assert game.world.together.account_friend("Ace", "Bee")    # (a homestead lets them in)

                r = await post(http, central + "/api/friends", {"token": tok["Gamma"]})
                assert r["playing"]["Alpha"]["character"] == "Ace" and r["playing"]["Alpha"]["place"] == "Kris's World"
                await a.close()
                await asyncio.sleep(1.0)
                r = await post(http, central + "/api/friends", {"token": tok["Gamma"]})
                assert "Alpha" not in r["playing"]                        # (gone from the game)

                sb.remove_friend_named("Ace")                             # (right-click: Remove friend)
                await asyncio.sleep(1.0)
                assert "Alpha" not in sb.central_friends["friends"] and "Ace" not in sb.friend_names()
                await b.close()
        finally:
            await grunner.cleanup()
            await crunner.cleanup()
    asyncio.run(go())


def test_a_hosted_games_files_are_kept_by_its_code_too(tmp_path, monkeypatch):
    """The central server keeps a hosted game's files by version: a new build with the same pictures has new code."""
    from server.relay import Relay
    gapp = make_app(ROOT, str(tmp_path / "game.db"), 5)
    game = gapp[GAME]
    relay = Relay(game, 8484)
    monkeypatch.setattr(game, "assets_version", lambda: "pictures")
    game.code_seen = "code-one"
    first = relay.page_version()
    game.code_seen = "code-two"
    assert first == "pictures-code-one" and relay.page_version() == "pictures-code-two" and len(first) <= 40
    monkeypatch.setattr(game, "assets_version", lambda: "")
    assert relay.page_version() == ""                                           # (none to go by: nothing's kept)
    game.store.close()


def test_a_game_hosted_for_friends_through_the_central_server(tmp_path, monkeypatch, confirmed):
    """Hosting for friends: the game connects out to the central server with its host's key (from the ticket the host
    came in with), its host's friends see it and come in through <central>/play/<id>/ (the page, its files, the game);
    anyone else, or a device with no account, is turned away."""
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        monkeypatch.setenv("DS_FRIENDS", "1")
        monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")
        gport = free_port()                                             # (the relay asks the game on its own port)
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Hostess's World", port=gport)
        grunner = web.AppRunner(gapp)
        await grunner.setup()
        await web.TCPSite(grunner, "127.0.0.1", gport).start()
        game = gapp[GAME]
        key = game.server_id()
        try:
            async with aiohttp.ClientSession() as http:
                tok = {}
                for n in ("Hostess", "Pal", "Stranger"):
                    tok[n] = (await post(http, central + "/api/register", {"name": n, **SIGNUP}))["token"]
                await post(http, central + "/api/friend", {"token": tok["Hostess"], "name": "Pal"})
                await post(http, central + "/api/friend", {"token": tok["Pal"], "name": "Hostess"})
                t = await post(http, central + "/api/ticket", {"token": tok["Hostess"], "server": key})
                host, m = await come_in(http, "ws://127.0.0.1:%d/ws" % gport, device_of("host"), ticket=t["ticket"],
                                        host="the-hosts-own-key", account="Hostess")
                assert m["t"] == "characters" and m["account"] == "Hostess"
                await host.close()
                for _ in range(100):                                    # (the relay opens with the host's key)
                    await asyncio.sleep(0.1)
                    if game.relay.up and game.host_friends:
                        break
                assert game.relay.up and game.host_friends == ["Pal"]
                r = await post(http, central + "/api/friends", {"token": tok["Pal"]})
                assert r["hosting"]["Hostess"] == {"key": key, "place": "Hostess's World"}

                via = central + "/play/%s/" % key
                async with http.get(via) as page:                       # (the game's page, through the central server)
                    assert page.status == 200 and "js/main.js" in await page.text()
                async with http.get(via + "js/net.js") as js:
                    assert js.status == 200 and "location.pathname" in await js.text()
                async with http.get(central + "/play/0123456789abcdef/") as gone:
                    assert gone.status == 404

                wsvia = "ws://127.0.0.1:%d/play/%s/ws" % (cport, key)
                t = await post(http, central + "/api/ticket", {"token": tok["Pal"], "server": key, "url": via})
                ws, m = await come_in(http, wsvia, device_of("pal"), ticket=t["ticket"])
                assert m["t"] == "characters" and m["account"] == "Pal"
                await ws.send_json({"t": "create", "name": "Palomino"})
                m = await replies(ws, ("welcome", "login_fail"))
                assert m["t"] == "welcome" and not m["host"]             # (relayed: never this machine)
                await ws.close()
                t = await post(http, central + "/api/ticket", {"token": tok["Stranger"], "server": key, "url": via})
                ws, m = await come_in(http, wsvia, device_of("stranger"), ticket=t["ticket"])
                assert m["t"] == "login_fail" and "friends" in m["reason"]
                await ws.close()
                ws, m = await come_in(http, wsvia, device_of("nobody"))
                assert m["t"] == "login_fail"                            # (a device alone: not through here)
                await ws.close()
        finally:
            await grunner.cleanup()
            await crunner.cleanup()
    asyncio.run(go())
