"""The central server: accounts, tickets into a game server, the remote servers list."""
import asyncio
import base64
import html
import json
import os
import re
import socket
import time

import aiohttp
import pytest
from aiohttp import web

from central.app import make_central, CENTRAL
from central.store import CentralStore
from server.app import make_app, GAME, PROGRESS
from tests.test_server import ROOT, come_in, device_of, replies


SIGNUP = {"password": "longpassword", "email": "player@example.com"}


@pytest.fixture
def confirmed(monkeypatch):
    """Sign-ups whose email counts at once (each its own): for the tests about what comes after."""
    monkeypatch.setattr(CentralStore, "set_pending_email",
                        lambda self, name, email: self.set_email(name, name.lower() + "@example.com"))


def quiet(gapp):
    """A remote server that hasn't announced itself: tickets by its id alone are good."""
    async def nothing(bye=False):
        pass
    gapp[GAME].announce = nothing


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
        for var in ("DS_CENTRAL", "DS_PUBLIC_URL", "DS_TRUST_PROXY"):
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
        db = capp[CENTRAL].store
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
                capp[CENTRAL].confirms = {}                                                  # (a new day's count)
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
        store = capp[CENTRAL].store
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
        store = crunner.app[CENTRAL].store
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
        quiet(gapp)
        grunner, gport = await run(gapp)
        game, url = gapp[GAME], "ws://127.0.0.1:%d/ws" % gport
        store = capp[CENTRAL].store
        try:
            async with aiohttp.ClientSession() as http:
                boss = (await post(http, c + "/api/register", {"name": "Boss", **SIGNUP,
                                                               "claim": capp[CENTRAL].claims.get("boss", "")}))["token"]
                pal = (await post(http, c + "/api/register", {"name": "Pal", **SIGNUP}))["token"]

                async def signup(name):
                    capp[CENTRAL].signups.clear()
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
                assert "hostgame1" in capp[CENTRAL].relays.tunnels
                count = store.count_accounts()

                assert (await post(http, c + "/api/admin/delete", {"token": boss, "name": "Kept"}))["ok"]
                await gone_from_everywhere("Kept", tok)
                await host.receive()
                assert host.closed and "hostgame1" not in capp[CENTRAL].relays.tunnels
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
                capp[CENTRAL].signups.clear()
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
        quiet(gapp)
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
                assert (await replies(ws, ("kicked",)))["reason"] == "Your Hallisium account is banned."
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
                assert "url" not in listed[0]                            # (a ticket brings it, to those signed in)
                info = await (await http.get("http://127.0.0.1:%d/api/info" % gport)).json()
                assert info == {"game": "shardsofashen", "remote": True}  # (never joined by its address)

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
                                                               "claim": capp[CENTRAL].claims["boss"]}))["token"]
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
        store = capp[CENTRAL].store
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


def test_a_servers_own_address_shows_a_browser_nothing(tmp_path, monkeypatch):
    """Through a client or the website: a ticket, or an app. /health and what a client asks stay."""
    monkeypatch.setenv("DS_TRUST_PROXY", "1")           # (so a call can say it isn't this machine)
    monkeypatch.delenv("DS_HOST_KEY", raising=False)
    away = {"X-Forwarded-For": "192.168.1.9"}

    async def status(http, url, headers=away):
        async with http.get(url, headers=headers) as r:
            return r.status, await r.read()

    async def go():
        runner, port = await run(make_app(ROOT, str(tmp_path / "game.db"), 5))
        own = make_app(ROOT, str(tmp_path / "own.db"), 5, own=True)
        orunner, oport = await run(own)
        at, there = "http://127.0.0.1:%d" % port, "http://127.0.0.1:%d" % oport
        try:
            async with aiohttp.ClientSession() as http:
                assert await status(http, at + "/") == (404, b"")
                for query in ("?ticket=abc", "?joined=1", "?app=android"):
                    assert (await status(http, at + "/" + query))[0] == 200, query
                assert (await status(http, at + "/", {}))[0] == 200         # (this machine)
                assert (await status(http, at + "/health"))[0] == 200
                assert (await status(http, at + "/api/info"))[0] == 200

                assert (await status(http, there + "/"))[0] == 404          # (an app's own game: closed)
                own[GAME].store.set_setting("lan_open", "1")
                assert (await status(http, there + "/"))[0] == 200          # (open: at the address its host gives)
        finally:
            await orunner.cleanup()
            await runner.cleanup()
    asyncio.run(go())


def test_a_remote_server_is_joined_at_its_listed_address_only(tmp_path, monkeypatch, confirmed):
    async def go():
        runner, port = await run(make_central(str(tmp_path / "central.db")))
        c = "http://127.0.0.1:%d" % port
        try:
            async with aiohttp.ClientSession() as http:
                key = (await post(http, c + "/api/announce", {"name": "Tower", "url": "https://play.example.com"}))["key"]
                token = (await post(http, c + "/api/register", {"name": "Wanderer", **SIGNUP}))["token"]

                async def ticket(url):
                    return (await post(http, c + "/api/ticket", {"token": token, "server": key, "url": url}))["ok"]
                assert await ticket("https://play.example.com")
                for elsewhere in ("https://evil.example", "http://192.168.1.20:8484", "http://[fd22:ad95:615f::5]:8484"):
                    assert not await ticket(elsewhere), elsewhere       # (its own network's address no different)
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_a_remote_servers_page_shows_only_for_a_ticket(tmp_path, monkeypatch):
    monkeypatch.setenv("DS_CENTRAL", "http://127.0.0.1:9")

    async def go():
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5)
        runner, port = await run(gapp)
        game = gapp[GAME]
        at = "http://127.0.0.1:%d/" % port
        try:
            assert game.remote()
            async with aiohttp.ClientSession() as http:
                for query in ("", "?app=android", "?joined=1"):         # (this machine, an app, an old token: nothing)
                    async with http.get(at + query) as r:
                        assert r.status == 404, query
                for query in ("?ticket=abc", "?joined=" + game.joined_token()):
                    async with http.get(at + query) as r:
                        assert r.status == 200, query
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_a_character_goes_from_a_public_server_to_a_device_and_never_back(tmp_path, monkeypatch):
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")
    monkeypatch.setenv("DS_CENTRAL", "http://127.0.0.1:9")

    async def go():
        pub = make_app(ROOT, str(tmp_path / "pub.db"), 5)
        own = make_app(ROOT, str(tmp_path / "own.db"), 5, own=True)
        prunner, pport = await run(pub)
        orunner, oport = await run(own)
        try:
            pub[GAME].store.create_account("Traveller", "", False, "a:Wanderer")
            pub[GAME].store.save_character("Traveller", {"level": 7, "last_seen": 1})
            async with aiohttp.ClientSession() as http:
                # (the public server's own side: the owner's copy, nobody else's)
                c = type("C", (), {"owner": "a:Wanderer", "host": False, "account": "Wanderer"})()
                sent = []

                async def send(_, m):
                    sent.append(m)
                pub[GAME].send = send
                await pub[GAME].export_character(c, {"name": "Traveller"})
                assert sent[-1]["t"] == "exported" and sent[-1]["save"]["level"] == 7
                c.owner = "a:Someone"
                await pub[GAME].export_character(c, {"name": "Traveller"})
                assert sent[-1]["t"] == "login_fail"
                save = sent[0]["save"]

                # (a public server never takes one, nor an app's game from anyone but its host)
                c.owner = "a:Wanderer"
                await pub[GAME].import_character(c, {"name": "Home", "save": save})
                assert sent[-1]["t"] == "login_fail" and pub[GAME].store.account("Home") is None

                ws = await http.ws_connect("ws://127.0.0.1:%d/ws" % oport)
                await replies(ws, ("hello",))
                await ws.send_json({"t": "auth", "device": "d" * 32, "host": "the-hosts-own-key"})
                got = await replies(ws, ("characters",))
                assert got["place"] == "own" and got["joined"] == ""
                await ws.send_json({"t": "import", "name": "Traveller", "save": save})
                got = await replies(ws, ("characters", "login_fail"))
                assert got["t"] == "characters" and [x["name"] for x in got["list"]] == ["Traveller"]
                await ws.send_json({"t": "import", "name": "Traveller", "save": "no"})
                assert (await replies(ws, ("characters", "login_fail")))["t"] == "login_fail"
                await ws.close()
        finally:
            await orunner.cleanup()
            await prunner.cleanup()
    asyncio.run(go())


def test_an_apps_game_tells_its_progress_anonymously(tmp_path, monkeypatch):
    from server.progress import Reporter
    monkeypatch.setenv("DS_CENTRAL", "http://127.0.0.1:9")
    gapp = make_app(ROOT, str(tmp_path / "own.db"), 5, own=True)
    game = gapp[GAME]
    game.store.create_account("Kris", "", False, "a:RealName")
    game.store.save_character("Kris", {"level": 3})
    told = []

    async def post(path, body, packed=False):
        told.append(body)
        return {"ok": True}
    game.central_post = post
    asyncio.run(Reporter(game).report())
    body = told[0]
    who = body["characters"][0]
    assert body["name"] == "" and who["account"] == "" and who["name"].startswith("Heir ")
    assert "Kris" not in json.dumps(body) and "RealName" not in json.dumps(body) and body["secret"]
    assert who["level"] == 3


def test_an_apps_game_is_opened_from_inside_it(tmp_path, monkeypatch, confirmed):
    """Closed as it starts; the network's needs no login, the internet's the host signed in; closing sends them home."""
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:     # (Windows keeps some back for UDP alone)
            s.bind(("0.0.0.0", 0))
            monkeypatch.setenv("DS_LAN_PORT", str(s.getsockname()[1]))
        gport = free_port()
        path = str(tmp_path / "game.db")
        gapp = make_app(ROOT, path, 5, name="Hostess's World", port=gport, own=True)
        grunner = web.AppRunner(gapp)
        await grunner.setup()
        await web.TCPSite(grunner, "127.0.0.1", gport).start()
        game = gapp[GAME]
        wsurl = "ws://127.0.0.1:%d/ws" % gport

        async def choose(ws, name):
            await ws.send_json({"t": "create", "name": name})
            return await replies(ws, ("welcome", "login_fail"))

        async def until(check):
            for _ in range(100):
                if check():
                    return True
                await asyncio.sleep(0.1)
            return False
        try:
            async with aiohttp.ClientSession() as http:
                assert game.lan_answer is None and game.relay_task is None
                guest, m = await come_in(http, wsurl, device_of("guest"), host="the-hosts-own-key")
                m = await choose(guest, "Lonely")
                assert m["reach"]["own"] and not m["reach"]["signed"] and not m["reach"]["internet"]
                await guest.send_json({"t": "lan", "open": True})           # (the network needs no login)
                m = await replies(guest, ("lan",))
                assert m["open"] and await until(lambda: game.lan_answer is not None)
                await guest.send_json({"t": "internet", "open": True})      # (the internet does)
                m = await replies(guest, ("internet",))
                assert not m["internet"] and game.relay_task is None
                await guest.send_json({"t": "lan", "open": False})
                assert await until(lambda: game.lan_answer is None)
                await guest.close()

                tok = {}
                for n in ("Hostess", "Pal"):
                    tok[n] = (await post(http, central + "/api/register", {"name": n, **SIGNUP}))["token"]
                await post(http, central + "/api/friend", {"token": tok["Hostess"], "name": "Pal"})
                await post(http, central + "/api/friend", {"token": tok["Pal"], "name": "Hostess"})
                key = game.server_id()
                t = await post(http, central + "/api/ticket", {"token": tok["Hostess"], "server": key})
                host, m = await come_in(http, wsurl, device_of("host"), ticket=t["ticket"],
                                        host="the-hosts-own-key", account="Hostess")
                m = await choose(host, "Hostess")
                assert m["reach"]["signed"] and m["reach"]["link"] == "%s/play/%s/" % (central, key)
                await host.send_json({"t": "internet", "open": True})
                m = await replies(host, ("internet",))
                assert m["internet"] and await until(lambda: game.relay.up and game.host_friends)

                # (the link as it's given: to the start screen to sign in; with a ticket, the page)
                async with http.get("%s/play/%s/" % (central, key), allow_redirects=False) as r:
                    assert r.status == 302 and r.headers["Location"] == "/?join=" + key
                t = await post(http, central + "/api/ticket", {"token": tok["Pal"], "server": key})
                async with http.get("%s/play/%s/?ticket=%s" % (central, key, t["ticket"])) as r:
                    assert r.status == 200
                pal, m = await come_in(http, "ws://127.0.0.1:%d/play/%s/ws" % (cport, key), device_of("pal"), ticket=t["ticket"])
                assert m["t"] == "characters"
                assert (await choose(pal, "Pal"))["t"] == "welcome"

                await host.send_json({"t": "internet", "open": False})
                m = await replies(host, ("internet",))
                assert not m["internet"] and await until(lambda: game.relay_task is None and not game.relay.up)
                assert await until(lambda: pal.closed or len(game.world.sessions) == 1)
                await asyncio.sleep(0.2)
                async with http.get("%s/play/%s/?joined=1" % (central, key)) as r:
                    assert r.status == 404                      # (the link's shut with it)
                await pal.close()
                await host.close()
                game.store.set_setting("lan_open", "1")
                game.store.set_setting("internet_open", "1")
        finally:
            await grunner.cleanup()
            await crunner.cleanup()

        # (starts again: closed again, whatever it was)
        again = make_app(ROOT, path, 5, port=free_port(), own=True)
        assert not again[GAME].lan_open and not again[GAME].for_friends()
    asyncio.run(go())


def test_the_ways_in_are_as_the_owner_said():
    """The website: sign-in, public servers, a friend's link. Local stays local: nothing about it goes to the central server."""
    with open(os.path.join(ROOT, "web", "home", "index.html"), encoding="utf-8") as f:
        home = f.read()
    for app_only in ('id="alone" class="tile go app-only"', 'id="friends-open" class="tile app-only"',
                     'id="local-open" class="tile app-only"', 'class="skip app-only"'):
        assert app_only in home, app_only
    assert 'id="host-open"' not in home and "/api/local" not in home
    assert 'id="remote-open"' in home and "app-only" not in home.split('id="remote-open"')[1].split(">")[0]


def test_friends_are_by_account_in_every_game(tmp_path, monkeypatch, confirmed):
    """Two Hallisium accounts: one asks, the other accepts (on the start screen, or in a game by right-click or the
    journal), and they're friends in every game, any character of theirs; a game says where they're playing; the
    world's old friends of a character move over to its account; a homestead lets an account's friends in."""
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Kris's World")
        quiet(gapp)
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
        monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")
        gport = free_port()                                             # (the relay asks the game on its own port)
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Hostess's World", port=gport, own=True)
        grunner = web.AppRunner(gapp)
        await grunner.setup()
        await web.TCPSite(grunner, "127.0.0.1", gport).start()
        game = gapp[GAME]
        key = game.server_id()
        game.store.set_setting("internet_open", "1")
        await game.internet_changed()
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
                assert game.relay.tunnel.compress               # (it's all compressed on its way through)
                r = await post(http, central + "/api/friends", {"token": tok["Pal"]})
                assert r["hosting"]["Hostess"] == {"key": key, "place": "Hostess's World"}

                via = central + "/play/%s/" % key
                async with http.get(via + "?joined=1") as page:        # (the game's page, through the central server)
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


# ----- how characters are getting on: what every game tells the central server, for its admin page
def admin_of(monkeypatch, name="Boss"):
    monkeypatch.setenv("DS_CENTRAL_ADMINS", name)


async def left(game, name):
    """Till that character's gone and saved for the last time, however busy this machine is."""
    for _ in range(1200):
        if name not in game.world.sessions:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(name + " never left")


def test_every_character_is_told_to_the_central_server_and_found_on_the_admin_page(tmp_path, monkeypatch, confirmed):
    """A game's characters, those playing and those long gone, an account's or a device's: found by name or by account,
    with their skills and quests. Only what's changed is sent; a device's key never is."""
    admin_of(monkeypatch)

    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        crunner, cport = await run(capp)
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Someone's PC", own=True)
        grunner, gport = await run(gapp)
        game = gapp[GAME]
        gapp[PROGRESS].cancel()                         # (it's told when this test says, not by the clock as well)
        wsurl = "ws://127.0.0.1:%d/ws" % gport
        told = []
        real_post = game.central_post

        async def spying(path, body, packed=False):
            if path == "/api/game/report":
                told.append((body, packed))
            return await real_post(path, body, packed)
        game.central_post = spying
        try:
            async with aiohttp.ClientSession() as http:
                boss = (await post(http, central + "/api/register", {"name": "Boss", "claim": capp[CENTRAL].claims["boss"], **SIGNUP}))["token"]
                ann = (await post(http, central + "/api/register", {"name": "Ann", **SIGNUP}))["token"]
                t = await post(http, central + "/api/ticket", {"token": ann, "server": game.server_id()})
                ws, m = await ticket_in(http, wsurl, t["ticket"], name="Annika")
                assert m["t"] == "welcome"
                s = game.world.sessions["Annika"]
                s.update_attribute("Passage", "=5")     # (a quest done, one under way, a skill raised)
                s.update_attribute("AmuletQuest", "=2")
                s.skill_xp[s.skill_index("Strength")] = 7.5
                await ws.close()
                await left(game, "Annika")
                # (a device's character, no account, played long ago)
                wd, m = await come_in(http, wsurl, device_of("lone device"))
                await wd.send_json({"t": "create", "name": "Loner"})
                assert (await replies(wd, ("welcome", "login_fail")))["t"] == "welcome"
                await wd.close()
                await left(game, "Loner")

                game.reporter.anonymous = lambda: False     # (the admin page's side, by name: anonymous has its own test)
                assert await game.reporter.report() is False
                body, packed = told[-1]
                assert packed and body["kind"] == "solo" and body["name"] == ""     # (a phone's or PC's name stays with it)
                names = {c["name"]: c for c in body["characters"]}
                assert set(names) == {"Annika", "Loner"}
                assert names["Annika"]["account"] == "Ann" and names["Loner"]["account"] == ""
                text = json.dumps(body)
                assert device_of("lone device") not in text and "d:" not in names["Loner"]["account"]
                assert "inventory" not in text and "look" not in text

                def ask(what, **more):
                    return post(http, central + "/api/admin/" + what, {"token": boss, **more})

                found = (await ask("characters", q="anni"))["characters"]
                assert [c["name"] for c in found] == ["Annika"] and found[0]["account"] == "Ann" and found[0]["done"] == 1
                assert [c["name"] for c in (await ask("characters", q="ann"))["characters"]] == ["Annika"]    # (by account)
                assert sorted(c["name"] for c in (await ask("characters"))["characters"]) == ["Annika", "Loner"]
                assert (await ask("characters", q="nobody"))["characters"] == []
                c = (await ask("character", server=found[0]["server"], name="annika"))["character"]
                assert {x["skill"]: x["level"] for x in c["skills"]}["Strength"] == 7
                quests = {q["quest"]: q for q in c["quests"]}
                assert quests["Passage to the Mainland"]["done"] and quests["Passage to the Mainland"]["finished"]
                assert quests["The Amulet of Succession"]["stage"] == 2 and not quests["The Amulet of Succession"]["done"]
                assert quests["The Amulet of Succession"]["doing"] and not quests["The Amulet of Succession"]["finished"]

                rows = {q["quest"]: q for q in (await ask("quests"))["quests"]}
                assert rows["Passage to the Mainland"]["done"] == 1 and rows["Passage to the Mainland"]["began"] == 1
                assert rows["Passage to the Mainland"]["main"] and rows["The Herbalist's Remedy"]["began"] == 0     # (every quest)
                r = await ask("quest", quest="The Amulet of Succession")
                assert [(x["stage"], x["count"]) for x in r["stages"]] == [(2, 1)] and r["stages"][0]["doing"]
                skills = {x["skill"]: x for x in (await ask("skills"))["skills"]}
                assert skills["Strength"]["highest"] == 7 and skills["Strength"]["characters"] == 2
                stats = await ask("stats")
                assert stats["characters"] == 2 and stats["with_account"] == 1 and stats["reporting"] == 1

                # (saved again with nothing new: nothing's sent; something new: only that character)
                n = len(told)
                game.store.save_character("Annika", game.store.load_character("Annika"))
                assert await game.reporter.report() is False and len(told) == n
                st = game.store.load_character("Annika")
                st["attributes"].append(["RemedyQuest", "2"])
                game.store.save_character("Annika", st)
                await game.reporter.report()
                assert [c["name"] for c in told[-1][0]["characters"]] == ["Annika"]
                c = (await ask("character", server=found[0]["server"], name="Annika"))["character"]
                assert {q["quest"]: q for q in c["quests"]}["The Herbalist's Remedy"]["done"]
                # (saved again in the same tick of the clock as the last that was told: still told)
                n = len(told)
                game.store.db.execute("UPDATE characters SET state = ?, updated = ? WHERE name = 'Annika'",
                                      (json.dumps({**st, "shards": 77}), float(game.store.setting("progress_mark"))))
                await game.reporter.report()
                assert len(told) == n + 1 and told[-1][0]["characters"][0]["shards"] == 77
                # (the central server away: told next time, not lost)
                st["attributes"].append(["DwarfQuest", "1"])
                game.store.save_character("Annika", st)
                game.central_post = lambda *a, **k: asyncio.sleep(0)
                await game.reporter.report()
                game.central_post = spying
                await game.reporter.report()
                assert "The Dwarf's Grudge" in told[-1][0]["characters"][0]["quests"]

                # (a deleted account's go with it, and don't come back)
                assert (await ask("delete", name="Ann"))["ok"]
                assert [c["name"] for c in (await ask("characters"))["characters"]] == ["Loner"]
                assert not (await ask("character", server=found[0]["server"], name="Annika")).get("ok")
                st["attributes"].append(["Extra", "1"])
                game.store.save_character("Annika", st)
                await game.reporter.report()
                assert [c["name"] for c in (await ask("characters"))["characters"]] == ["Loner"]

                # (blocked: what it sent goes, and it isn't heard)
                assert (await ask("block", key=found[0]["server"], on=True))["ok"]
                assert (await ask("characters"))["characters"] == []
                got = await post(http, central + "/api/game/report", {"secret": game.reporter.secret(),
                                                                      "characters": [{"name": "Junk"}]})
                assert got["blocked"] and (await ask("characters"))["characters"] == []

                # (it's only for an admin)
                assert not (await post(http, central + "/api/admin/characters", {"token": ""}))["ok"]
        finally:
            await grunner.cleanup()
            await crunner.cleanup()
    asyncio.run(go())


def test_a_report_is_taken_only_as_far_as_it_should_be(tmp_path, monkeypatch, confirmed):
    """Anyone can send one: a secret too short, things out of range or of the wrong kind, an account that isn't there;
    nobody writes under another's key; zipped comes through; and the DS_PROGRESS off switch."""
    from server.progress import Reporter
    admin_of(monkeypatch)

    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        db = capp[CENTRAL].store
        try:
            async with aiohttp.ClientSession() as http:
                await post(http, c + "/api/register", {"name": "Real", **SIGNUP})
                url = c + "/api/game/report"
                assert not (await post(http, url, {"secret": "short", "characters": []}))["ok"]
                mine, other = "a" * 32, "b" * 32
                r = await post(http, url, {"secret": mine, "kind": "evil", "characters": [
                    {"name": "<b>Bold</b>", "level": "99999", "skills": {"Strength": [3, "1e308"], "Bad": "x"},
                     "quests": {"Q": [1, 1], "Bad": 5}, "map": "x" * 500},
                    {"name": "Forged", "account": "Nobody"},    # (no such account: not taken)
                    {"name": "Fine", "account": "Real"}, {"name": ""}, "not a character"]})
                assert r["ok"] and r["took"] == 2
                rows = {x["name"]: x for x in db.find_characters()}
                assert set(rows) == {"bBoldb", "Fine"} and rows["bBoldb"]["level"] == 1000 and len(rows["bBoldb"]["map"]) == 24
                assert rows["bBoldb"]["kind"] == "local"
                assert await post(http, url, {"secret": other, "characters": [{"name": "Fine", "level": 2}]})
                assert sum(1 for x in db.find_characters() if x["name"] == "Fine") == 2     # (each game's its own)
                assert db.find_characters("Fine", rows["Fine"]["server"])[0]["level"] == 1  # (the other didn't touch it)
                for bad in ([], "x", None, 5, {"a": 1}):
                    assert (await post(http, url, {"secret": mine, "characters": bad}))["took"] == 0
                many = [{"name": "N%d" % i} for i in range(200)]
                assert (await post(http, url, {"secret": mine, "characters": many}))["took"] == 50
                capp[CENTRAL].reports.clear()
                import gzip
                async with http.post(url, data=gzip.compress(json.dumps({"secret": "c" * 32, "characters": [{"name": "Zip"}]}).encode()),
                                     headers={"Content-Type": "application/json", "Content-Encoding": "gzip"}) as z:
                    assert (await z.json())["took"] == 1
                # (a broken character in it, or an impossible number: refused or clamped, and the next is heard as ever)
                r = await post(http, url, {"secret": mine, "characters": [{"name": "Broken", "map": "\ud800"}]})
                assert not r["ok"]
                async with http.post(url, data='{"secret":"%s","characters":[{"name":"Huge","level":1e999,"gold":-1e999,'
                                     '"skills":{"Strength":[1e999,1e999]},"quests":{"Q":[1e999,1]}}]}' % mine,
                                     headers={"Content-Type": "application/json"}) as r:
                    assert r.status == 200 and (await r.json())["took"] == 1
                assert db.find_characters("Huge")[0]["level"] == 1
                assert (await post(http, url, {"secret": mine, "characters": [{"name": "After"}]}))["took"] == 1
                assert db.find_characters("After") and not db.find_characters("Broken")
                # (too many from one address)
                capp[CENTRAL].reports.clear()
                for _ in range(90):
                    await post(http, url, {"secret": mine, "characters": []})
                assert not (await post(http, url, {"secret": mine, "characters": []}))["ok"]
                # (nor new games without end)
                capp[CENTRAL].reports.clear()
                capp[CENTRAL].new_reporters.clear()
                for i in range(20):
                    assert (await post(http, url, {"secret": ("%02d" % i) * 16, "characters": []}))["ok"]
                assert not (await post(http, url, {"secret": "d" * 32, "characters": []}))["ok"]
        finally:
            await runner.cleanup()
    asyncio.run(go())

    class G:
        central_url = staticmethod(lambda: "http://central")
    monkeypatch.setenv("DS_PROGRESS", "0")
    assert not Reporter(G).on()
    monkeypatch.delenv("DS_PROGRESS")
    assert Reporter(G).on()


def test_progress_is_read_right_from_an_old_save():
    """Skills from before they went to 25, and under old names; gold in the pack and the bank; what's not begun isn't told."""
    from server.progress import progress_of
    quests = [("One", {"ATTRIBUTE": "OneQ", "DONE": "3"}), ("Two", {"ATTRIBUTE": "TwoQ", "DONE": "3"}),
              ("Three", {"ATTRIBUTE": "ThreeQ", "DONE": "0"}), ("Four", {"ATTRIBUTE": "FourQ", "DONE": "2"}), ("Five", {})]
    c = progress_of({"skills": {"Magic": 40, "Smithing": 10, "Crafting": 20, "Strength": 0.5}, "level": 9, "map": "1,2,0",
                     "attributes": [["oneq", "3"], ["TWOQ", 1], ["ThreeQ", "4"], ["junk"]],
                     "inventory": [["Gold_Coin(s)", 7, 0], ["Log", 3, 0]], "bank": [["Gold_Coin(s)", 5, []]], "shards": 4},
                    quests, 25)
    assert c["skills"]["Channeling"] == [20, 20.0] and c["skills"]["Crafting"] == [10, 10.0]    # (out of 50, then)
    assert c["skills"]["Strength"][0] == 1 and "Magic" not in c["skills"]
    assert c["quests"] == {"One": [3, 1], "Two": [1, 0], "Three": [4, 0]}
    assert c["gold"] == 12 and c["shards"] == 4 and c["level"] == 9 and c["map"] == "1,2,0"
    assert progress_of({}, quests, 25) == {"level": 1, "shards": 0, "gold": 0, "map": "", "skills": {}, "quests": {}}


# ----- signing in with Google, with a pretend Google (only its token endpoint: its sign-in page is theirs)
def id_token(claims):
    import base64
    part = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()     # noqa: E731
    return "%s.%s.sig" % (part({"alg": "RS256"}), part(claims))


class PretendGoogle:
    """Its token endpoint, answering for the next sign-in: who it says it is."""

    def __init__(self):
        self.who = {}
        self.asked = []

    async def token(self, request):
        form = await request.post()
        self.asked.append(dict(form))
        if form.get("code") == "refused":
            return web.json_response({"error": "invalid_grant"}, status=400)
        return web.json_response({"id_token": id_token({**self.nonce_for, **self.who})})

    async def sign_in(self, http, c, to="home", cookies=True, **who):
        """Off to it from /auth/google, and back to /auth/google/done: the response."""
        self.who = {"iss": "https://accounts.google.com", "aud": "the-client-id", "exp": time.time() + 600,
                    "email_verified": True, **who}
        async with http.get(c + "/auth/google?to=" + to, allow_redirects=False) as off:
            assert off.status == 302 and off.headers["Location"].startswith("https://accounts.google.com/")
            from urllib.parse import urlsplit, parse_qs
            q = {k: v[0] for k, v in parse_qs(urlsplit(off.headers["Location"]).query).items()}
            assert q["client_id"] == "the-client-id" and q["scope"] == "openid email" and q["code_challenge_method"] == "S256"
            assert q["redirect_uri"] == c + "/auth/google/done"
        self.nonce_for = {"nonce": q["nonce"]}
        back = await http.get(c + "/auth/google/done", params={"state": q["state"], "code": who.get("code", "a-code")},
                              allow_redirects=False)
        self.state = q["state"]
        return back


def code_from(back):
    return back.headers["Location"].split("#google=")[1]


async def words(r):
    """A page's words, as they read."""
    return html.unescape(await r.text())


def test_signing_in_with_google(tmp_path, monkeypatch):
    """New: a name to choose (as a sign-up's checks), its email kept like anyone's, confirmed by Google. Again: signed in.
    An account with that address confirmed: Google gets into it, nothing kept. One made with Google has no password. A
    cookie ties Google's answer to the browser that set off, so nobody can sign you in as them."""
    from central import google, mail
    monkeypatch.setenv("DS_SMTP_HOST", "test")
    mail.SENT.clear()
    monkeypatch.setenv("DS_CENTRAL_ADMINS", "Boss")

    async def go():
        fake = PretendGoogle()
        gapp = web.Application()
        gapp.router.add_post("/token", fake.token)
        grunner, gport = await run(gapp)
        monkeypatch.setattr(google, "TOKEN_URL", "http://127.0.0.1:%d/token" % gport)
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        central = capp[CENTRAL]
        db = central.store
        jar = aiohttp.CookieJar(unsafe=True)
        try:
            async with aiohttp.ClientSession(cookie_jar=jar) as http:
                # (not set up: no button, no way in)
                assert not (await (await http.get(c + "/api/hello")).json())["google"]
                async with http.get(c + "/auth/google", allow_redirects=False) as r:
                    assert r.status == 200 and "can't sign in with Google" in await words(r)
                monkeypatch.setenv("DS_GOOGLE_CLIENT_ID", "the-client-id")
                monkeypatch.setenv("DS_GOOGLE_CLIENT_SECRET", "the-secret")
                assert (await (await http.get(c + "/api/hello")).json())["google"]

                back = await fake.sign_in(http, c, sub="g-1", email="new@gmail.com")
                assert back.status == 302 and back.headers["Location"].startswith("/#google=")
                assert fake.asked[-1]["code"] == "a-code" and fake.asked[-1]["client_secret"] == "the-secret"
                assert len(fake.asked[-1]["code_verifier"]) >= 43       # (PKCE)
                code = code_from(back)
                api = c + "/api/google"
                r = await post(http, api, {"code": code})
                assert r["ok"] and r["choose"] and r["email"] == "new@gmail.com" and "token" not in r
                # (a sign-up's checks)
                for bad, word in (("admin", "kept back"), ("", "Pick a name"), ("Two Words", "spaces")):
                    r = await post(http, api, {"code": code, "name": bad})
                    assert not r["ok"] and r["choose"] and word in r["text"]
                r = await post(http, api, {"code": code, "name": "Boss"})
                assert not r["ok"] and r["claim"]               # (kept for the admin: only with the code)
                await post(http, c + "/api/register", {"name": "Taken", "password": "longpassword", "email": "taken@example.com"})
                r = await post(http, api, {"code": code, "name": "Taken"})
                assert not r["ok"] and r["choose"] and "taken" in r["text"]
                r = await post(http, api, {"code": code, "name": "Newcomer"})
                assert r["ok"] and r["name"] == "Newcomer" and r["token"] and r["made"] and not r["needs_email"]
                tok = r["token"]
                me = await post(http, c + "/api/account", {"token": tok})
                assert me["email"] == "new@gmail.com" and me["pending"] == ""     # (Google has verified it)
                t = await post(http, c + "/api/ticket", {"token": tok, "server": "0123456789abcdef"})
                assert t["ok"]                                  # (so it can join a game at once)
                assert not (await post(http, api, {"code": code}))["ok"]          # (a code's good once)
                # (no password of its own: nothing logs in with an empty one)
                assert not (await post(http, c + "/api/login", {"name": "Newcomer", "password": ""}))["ok"]

                # (again: signed in, no name to choose, and a code in the admin page's fragment if it asked)
                back = await fake.sign_in(http, c, to="admin", sub="g-1", email="changed@gmail.com")
                assert back.headers["Location"].startswith("/admin#google=")
                r = await post(http, api, {"code": code_from(back)})
                assert r["ok"] and r["name"] == "Newcomer" and r["token"] and not r.get("made")

                # (an app: the page shows the code to type)
                back = await fake.sign_in(http, c, to="app", sub="g-1", email="new@gmail.com")
                page = await words(back)
                assert back.status == 200 and "type this code" in page and "start screen" not in page
                assert back.headers["Cache-Control"] == "no-store"
                typed = re.search(r"\b([A-Z2-9]{4}-[A-Z2-9]{4})\b", page).group(1)
                r = await post(http, api, {"code": typed.lower().replace("-", " ")})
                assert r["ok"] and r["name"] == "Newcomer"

                # (its email is kept like anyone's: found by it, shown to the admin, and nobody else can have it)
                assert db.account_by_email("new@gmail.com")[0] == "Newcomer"
                r = await post(http, c + "/api/register", {"name": "Copycat", "password": "longpassword", "email": "new@gmail.com"})
                assert not r["ok"] and "another account" in r["text"]

                # (an account with that address confirmed: Google gets into it, nothing's kept, and its password goes on working)
                await post(http, c + "/api/register", {"name": "Waiting", "password": "longpassword", "email": "wait@gmail.com"})
                back = await fake.sign_in(http, c, sub="g-2", email="wait@gmail.com")
                early = code_from(back)                         # (only waiting to be confirmed: not on the account yet)
                assert (await post(http, api, {"code": early}))["choose"]
                db.set_email("Waiting", "wait@gmail.com")
                r = await post(http, api, {"code": early, "name": "Latecomer"})      # (confirmed while they chose a name)
                assert not r["ok"] and "on an account here" in r["text"] and db.account("Latecomer") is None
                back = await fake.sign_in(http, c, sub="g-3", email="WAIT@gmail.com")
                r = await post(http, api, {"code": code_from(back)})
                assert r["ok"] and r["name"] == "Waiting" and r["token"] and not r.get("made")
                assert db.google_of("Waiting") == "" and db.account_by_google("g-3") is None
                assert (await post(http, c + "/api/login", {"name": "Waiting", "password": "longpassword"}))["ok"]
                # (banned: not by this way either)
                db.set_banned("Waiting", "testing")
                back = await fake.sign_in(http, c, sub="g-3", email="wait@gmail.com")
                assert back.status == 200 and "banned" in await words(back)
                db.set_banned("Waiting", "")
                # (its email changed: that Google account no longer gets in, and may make its own)
                db.set_email("Waiting", "elsewhere@example.com")
                back = await fake.sign_in(http, c, sub="g-3", email="wait@gmail.com")
                assert (await post(http, api, {"code": code_from(back)}))["choose"]
                # (an account made with one Google account isn't got into by another with its address)
                back = await fake.sign_in(http, c, sub="g-99", email="new@gmail.com")
                assert back.status == 200 and "another Google account" in await words(back)

                # (nor the other way: an account made with Google gets no password, and says how it signs in)
                central.fails.clear()
                r = await post(http, c + "/api/login", {"name": "Newcomer", "password": "anything at all"})
                assert not r["ok"] and "signs in with Google" in r["text"] and "token" not in r
                mail.SENT.clear()
                r = await post(http, c + "/api/forgot", {"who": "new@gmail.com"})
                told = await post(http, c + "/api/forgot", {"who": "nobody@gmail.com"})
                assert r["ok"] and r["text"] == told["text"]    # (the same answer, account or none)
                assert len(mail.SENT) == 1 and "Continue with Google" in mail.SENT[0][2]
                assert db.mail_code("Newcomer") == ""           # (no code, so no new password)
                r = await post(http, c + "/api/reset", {"name": "Newcomer", "code": "AAAA-BBBB", "password": "longpassword"})
                assert not r["ok"] and db.account("Newcomer")[1] == ""

                # (Google's word has to hold up)
                for bad, word in (({"email_verified": False}, "verified"), ({"aud": "someone-else"}, "wasn't for this game"),
                                  ({"iss": "https://evil.example"}, "wasn't for this game"),
                                  ({"exp": time.time() - 3600}, "run out"), ({"email": "not an address"}, "can't be used")):
                    back = await fake.sign_in(http, c, **{"sub": "g-9", "email": "x@gmail.com", **bad})
                    assert back.status == 200 and word in await words(back), bad
                back = await fake.sign_in(http, c, sub="g-9", email="x@gmail.com", code="refused")
                assert "didn't accept" in await words(back)
                # (its nonce must be this sign-in's)
                orig = fake.token

                async def wrong_nonce(request):
                    await request.post()
                    return web.json_response({"id_token": id_token({**fake.who, "nonce": "another"})})
                gapp2 = web.Application()
                gapp2.router.add_post("/token", wrong_nonce)
                g2, g2port = await run(gapp2)
                monkeypatch.setattr(google, "TOKEN_URL", "http://127.0.0.1:%d/token" % g2port)
                back = await fake.sign_in(http, c, sub="g-9", email="x@gmail.com")
                assert "wasn't for this game" in await words(back)
                await g2.cleanup()
                monkeypatch.setattr(google, "TOKEN_URL", "http://127.0.0.1:%d/token" % gport)
                assert orig

                # (the browser that set off: another's answer, or another browser, is nothing)
                async with http.get(c + "/auth/google", allow_redirects=False) as off:
                    state = re.search(r"state=([^&]+)", off.headers["Location"]).group(1)
                async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as stranger:
                    r = await stranger.get(c + "/auth/google/done", params={"state": state, "code": "x"})
                    assert "run out" in await words(r)
                r = await http.get(c + "/auth/google/done", params={"state": "made-up", "code": "x"})
                assert "run out" in await words(r)
                r = await http.get(c + "/auth/google/done", params={"state": state, "error": "access_denied"})
                assert "Nothing has changed" in await words(r)
                r = await http.get(c + "/auth/google/done", params={"state": state, "code": "x"})
                assert "run out" in await words(r)              # (once)

                # (banned, deleted)
                db.set_banned("Newcomer", "testing")
                back = await fake.sign_in(http, c, sub="g-1", email="new@gmail.com")
                assert back.status == 200 and "banned" in await words(back)
                db.set_banned("Newcomer", "")
                back = await fake.sign_in(http, c, sub="g-1", email="new@gmail.com")
                code = code_from(back)
                db.set_banned("Newcomer", "since")              # (between the two)
                assert "banned" in (await post(http, api, {"code": code}))["text"]
                db.set_banned("Newcomer", "")
                db.delete_account("Newcomer", True)
                assert db.account_by_google("g-1") is None      # (kept name, nothing else: they'd make a new one)
                back = await fake.sign_in(http, c, sub="g-1", email="new@gmail.com")
                assert (await post(http, api, {"code": code_from(back)}))["choose"]

                # (guessing codes is limited, by address)
                wrong = [await post(http, api, {"code": "AAAA-%04d" % i}) for i in range(8)]
                assert "Too many tries" in wrong[-1]["text"]
                # (and no name's reused by a flood of pending ones: the oldest go)
                central.google_flows.update({str(i): {"at": time.time(), "to": "home"} for i in range(3000)})
                central.trim_google()
                assert len(central.google_flows) == 2000
        finally:
            await runner.cleanup()
            await grunner.cleanup()
    asyncio.run(go())


def test_an_app_opens_google_in_a_real_browser():
    """Google refuses to sign in inside an app's web view: both apps can open the phone's or PC's own browser, http(s) only."""
    with open(os.path.join(ROOT, "web", "home", "index.html"), encoding="utf-8") as f:
        page = f.read()
    assert 'id="google"' in page and "app.openLink(url)" in page and "/auth/google?to=app" in page
    with open(os.path.join(ROOT, "android", "app", "src", "main", "java", "io", "github", "kriscs1", "shardsofashen",
                           "MainActivity.java"), encoding="utf-8") as f:
        android = f.read()
    assert "public void openLink(String url)" in android and "ACTION_VIEW" in android
    with open(os.path.join(ROOT, "desktop", "app.py"), encoding="utf-8") as f:
        desktop = f.read()
    assert "def openLink(self, url)" in desktop and "openLink: (url)" in desktop


# ----- SQL injection: what's typed never becomes part of a query
INJECTIONS = ["' OR '1'='1", "' OR 1=1 --", "Robert'); DROP TABLE accounts;--", "x' UNION SELECT name, password, 1, 1, 1, 1, 1 FROM accounts --",
              "\" OR \"\"=\"", "admin'--", "%", "_", "\\", "'; ATTACH DATABASE 'x.db' AS x;--", "a@b.co'; DROP TABLE tokens;--"]
ODD = [None, 5, 1.5, True, [], ["a"], {"a": "b"}, "\ud800", "\x00", "a\x00b", "x" * 100000]


def test_sql_injection_on_every_way_in(tmp_path, monkeypatch, confirmed):
    """Whatever's sent to signing up, logging in and the rest: nobody's let in, nothing's broken, and there's no 500."""
    admin_of(monkeypatch)
    monkeypatch.setenv("DS_REGISTER_PER_DAY", "0")
    monkeypatch.setenv("DS_SMTP_HOST", "test")

    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        central = capp[CENTRAL]
        db = central.store
        try:
            async with aiohttp.ClientSession() as http:
                boss = (await post(http, c + "/api/register", {"name": "Boss", "claim": central.claims["boss"], **SIGNUP}))["token"]
                victim = await post(http, c + "/api/register", {"name": "Victim", **SIGNUP})
                assert victim["ok"]
                tables = [r[0] for r in sqlite_tables(tmp_path / "central.db")]
                paths = ["register", "login", "reset", "forgot", "me", "logout", "account", "email", "ticket", "verify", "friends",
                         "friend", "game/friends", "game/standing", "game/report", "goodbye", "announce", "google", "admin/accounts"]
                fields = ("name", "password", "email", "who", "code", "token", "ticket", "server", "grant", "key", "secret", "q",
                          "claim", "url", "remove", "characters")

                async def send(path, value):
                    central.fails.clear()               # (the limits aren't what's being tried)
                    central.signups.clear()
                    central.announces.clear()
                    central.reports.clear()
                    async with http.post(c + "/api/" + path, data=json.dumps({f: value for f in fields}),
                                         headers={"Content-Type": "application/json"}) as r:
                        assert r.status < 500, (path, value, r.status)
                        return await r.json(content_type=None) if r.status == 200 else {}

                for path in paths:
                    for value in INJECTIONS + ODD:
                        got = await send(path, value)
                        if path in ("login", "me", "account", "friends", "ticket", "reset"):
                            assert not got.get("token") and got.get("name") not in ("Boss", "Victim"), (path, value)
                        if path == "admin/accounts":
                            assert not got.get("ok"), value     # (its token's the same nonsense)
                # (a search for them finds what it says, not everyone; by an admin, each as plain text)
                for value in INJECTIONS:
                    found = await post(http, c + "/api/admin/accounts", {"token": boss, "q": value})
                    assert found["ok"] and found["accounts"] == [], value
                    found = await post(http, c + "/api/admin/characters", {"token": boss, "q": value})
                    assert found["ok"] and found["characters"] == [], value
                    assert (await post(http, c + "/api/admin/character", {"token": boss, "server": value, "name": value})).get("ok") is False
                    assert (await post(http, c + "/api/admin/quest", {"token": boss, "quest": value, "server": value}))["stages"] == []
                # (what can get as far as being kept, in a name, comes back as it went in, harmlessly)
                await post(http, c + "/api/game/report", {"secret": "e" * 32, "name": INJECTIONS[2], "version": INJECTIONS[0],
                                                          "characters": [{"name": "Plain", "map": INJECTIONS[2], "quests": {INJECTIONS[2]: [1, 0]},
                                                                          "skills": {INJECTIONS[1]: [1, 1]}}]})
                row = db.find_characters("Plain")[0]
                assert row["map"] == INJECTIONS[2][:24] and row["place"] == INJECTIONS[2]
                assert (await post(http, c + "/api/admin/quest", {"token": boss, "quest": INJECTIONS[2]}))["stages"][0]["count"] == 1

                # (it's all still there, and still works)
                assert [r[0] for r in sqlite_tables(tmp_path / "central.db")] == tables
                assert (await post(http, c + "/api/me", {"token": victim["token"]}))["name"] == "Victim"
                central.fails.clear()
                assert (await post(http, c + "/api/login", {"name": "Victim", "password": SIGNUP["password"]}))["ok"]
                # (the name it was asked to log in as was cleaned of what makes it dangerous, not merely quoted)
                assert not (await post(http, c + "/api/register", {"name": "'; DROP--", **SIGNUP})).get("name", "").count("'")
        finally:
            await runner.cleanup()
    asyncio.run(go())


def sqlite_tables(path):
    import sqlite3
    db = sqlite3.connect(str(path))
    try:
        return db.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
    finally:
        db.close()


def test_every_query_keeps_its_values_out_of_its_text():
    """In the central server's and the game server's stores, a query's text is this file's own words: never made with
    a value in it. Only a table or column named in the code's own lists may be put in with %s."""
    import ast
    trusted = {"table", "col", "kind", "waiting", "SCHEMA", "INDEXES", "bad"}       # (bound only to literals in the code)

    def safe(node):
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
            return safe(node.left) and (safe(node.right) or isinstance(node.op, ast.Mod) and names_ok(node.right))
        if isinstance(node, ast.IfExp):
            return safe(node.body) and safe(node.orelse)
        if isinstance(node, ast.Name):
            return node.id in trusted
        return False

    def names_ok(node):
        if isinstance(node, ast.Tuple):
            return all(names_ok(e) for e in node.elts)
        return isinstance(node, ast.Name) and node.id in trusted

    checked = 0
    for rel in ("central/store.py", "server/store.py"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for fn in ast.walk(tree):
            if isinstance(fn, ast.Call) and isinstance(fn.func, ast.Attribute) and fn.func.attr in ("execute", "executemany",
                                                                                                    "executescript") and fn.args:
                checked += 1
                assert safe(fn.args[0]), "%s:%d: a query made from something else" % (rel, fn.lineno)
        for fn in ast.walk(tree):                       # (a name called table is only ever one of the file's own)
            if isinstance(fn, ast.For) and isinstance(fn.target, ast.Name) and fn.target.id == "table":
                assert isinstance(fn.iter, ast.Tuple) and all(isinstance(e, ast.Constant) for e in fn.iter.elts), (rel, fn.lineno)
    assert checked > 60


def test_the_central_database_can_only_read_and_write_rows(tmp_path):
    """Should a query ever go wrong: no dropping or altering a table, no reaching another file, no reading the schema."""
    import sqlite3
    db = CentralStore(str(tmp_path / "c.db"))
    for bad in ("DROP TABLE accounts", "ALTER TABLE accounts ADD COLUMN x", "CREATE TABLE t (a)", "ATTACH DATABASE 'x.db' AS x",
                "SELECT sql FROM sqlite_master", "PRAGMA writable_schema = 1", "DELETE FROM sqlite_master"):
        with pytest.raises(sqlite3.DatabaseError):
            db.db.execute(bad)
    db.create_account("Ann", "h")                       # (and it still does its work)
    assert db.account("ann")[0] == "Ann"
    db.db.close()
    again = CentralStore(str(tmp_path / "c.db"))        # (opened again, its columns and indexes checked: no trouble)
    assert again.account("Ann")
    again.db.close()


# ----- the central server: light on the wire and on itself
def test_the_central_server_answers_in_as_few_bytes_as_it_can(tmp_path, confirmed):
    async def go():
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        db = capp[CENTRAL].store
        try:
            async with aiohttp.ClientSession() as http:
                # (the list as a browser has it: a few bytes)
                async with http.get(c + "/api/servers") as r:
                    tag = r.headers["ETag"]
                    assert await r.json() == []
                async with http.get(c + "/api/servers", headers={"If-None-Match": tag}) as r:
                    assert r.status == 304 and await r.read() == b""
                # (the start screen's pictures aren't asked for each time, and the page only if it's changed)
                async with http.get(c + "/logo.png") as r:
                    assert "max-age=86400" in r.headers["Cache-Control"]
                # (and it has its icon in a browser's tab)
                async with http.get(c + "/favicon.png") as r:
                    assert r.status == 200 and r.content_type == "image/png"
                async with http.get(c + "/") as r:
                    tag = r.headers["ETag"]
                async with http.get(c + "/", headers={"If-None-Match": tag}) as r:
                    assert r.status == 304
                # (no spaces in an answer)
                async with http.get(c + "/api/hello") as r:
                    assert '": ' not in await r.text()

                # (a game asking after its player's friends each minute: "same" if nothing's changed)
                ann = (await post(http, c + "/api/register", {"name": "Ann", **SIGNUP}))["token"]
                bob = (await post(http, c + "/api/register", {"name": "Bob", **SIGNUP}))["token"]
                t = await post(http, c + "/api/ticket", {"token": ann, "server": "0123456789abcdef"})
                grant = (await post(http, c + "/api/verify", {"ticket": t["ticket"], "server": "0123456789abcdef"}))["grant"]
                full = await post(http, c + "/api/game/friends", {"grant": grant, "playing": "Hero", "place": "Here"})
                assert full["have"] and "friends" in full
                same = await post(http, c + "/api/game/friends", {"grant": grant, "playing": "Hero", "place": "Here", "have": full["have"]})
                assert same["same"] and "friends" not in same
                await post(http, c + "/api/friend", {"token": bob, "name": "Ann"})
                news = await post(http, c + "/api/game/friends", {"grant": grant, "playing": "Hero", "have": full["have"]})
                assert not news.get("same") and news["asking"] == ["Bob"]
                # (a game a version old sends no "have", and gets the whole of it as it always did)
                assert "friends" in await post(http, c + "/api/game/friends", {"grant": grant})

                # (where many friends are playing: one query, by any case)
                for n in ("Ann", "Bob"):
                    db.set_playing(n, "s", "p", n + "'s hero")
                assert set(db.playing_of(["ann", "BOB", "Nobody"])) == {"ann", "BOB"}
                assert db.playing_of([]) == {}

                # (old rows and the counts kept in memory are cleared without a game having to call)
                # (long ago by the monotonic clock: 0.0 isn't, on a machine only just started)
                capp[CENTRAL].fails[("addr", "1.2.3.4")] = [time.monotonic() - 9999]
                capp[CENTRAL].signups["1.2.3.4"] = ["19990101"]
                capp[CENTRAL].housekeeping()
                assert ("addr", "1.2.3.4") not in capp[CENTRAL].fails and "1.2.3.4" not in capp[CENTRAL].signups
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_a_friends_browser_is_not_sent_a_file_it_has(tmp_path):
    """Through the central server, a game's files are known by its version: a browser that has one gets a 304 without the
    host being asked; and what's kept here stays under its limit, the oldest going first."""
    from central import relay
    from central.relay import Relays, Tunnel

    class Ws:
        closed = False

        async def send_str(self, text):
            sends.append(json.loads(text))
            f = tunnel.asks[sends[-1]["r"]]
            f.set_result({"s": 200, "ct": "text/plain", "cc": "public, max-age=3600", "b": "aGVsbG8="})
    sends = []
    relays = Relays(None)
    tunnel = Tunnel(Ws(), "Host", "gamekey", "A game", "v1")
    relays.tunnels["gamekey"] = tunnel

    async def go():
        app = web.Application()
        app.router.add_get("/play/{key}/{path:.*}", relays.play)
        runner, port = await run(app)
        url = "http://127.0.0.1:%d/play/gamekey/assets/a.png" % port
        try:
            async with aiohttp.ClientSession() as http:
                async with http.get(url) as r:
                    tag = r.headers["ETag"]
                    assert r.status == 200 and await r.read() == b"hello"
                assert len(sends) == 1
                async with http.get(url) as r:
                    assert r.status == 200 and await r.read() == b"hello" and len(sends) == 1      # (kept here)
                relays.kept.clear()
                async with http.get(url, headers={"If-None-Match": tag}) as r:
                    assert r.status == 304 and len(sends) == 1                                     # (the host's not asked)
                tunnel.version = "v2"
                async with http.get(url, headers={"If-None-Match": tag}) as r:
                    assert r.status == 200                                                         # (a new version: new files)
        finally:
            await runner.cleanup()
    asyncio.run(go())

    relays = Relays(None)
    big = (200, "", "", b"x" * (relay.KEPT_MOST // 2 + 1))
    relays.keep(("v", "a"), big)
    relays.keep(("v", "a"), big)                        # (the same one twice: counted once)
    assert relays.kept_bytes == len(big[3])
    relays.keep(("v", "b"), big)
    relays.keep(("v", "c"), big)
    assert list(relays.kept) == [("v", "c")] or list(relays.kept) == [("v", "b"), ("v", "c")]
    assert relays.kept_bytes <= relay.KEPT_MOST


def test_the_admin_page_is_plain_and_light():
    """The browser's own font and colours, no pictures and nothing from anywhere else; a phone's layout; escapes what
    game servers send."""
    with open(os.path.join(ROOT, "central", "pages", "admin.html"), encoding="utf-8") as f:
        page = f.read()
    assert len(page) < 25000
    for fancy in ("url(", "gradient", "border-radius", "box-shadow", "animation", "Palatino", "<img", "http://", "https://"):
        assert fancy not in page, fancy
    assert "@media (max-width: 640px)" in page and "color-scheme: light dark" in page
    assert 'id="q"' in page and "showCharacter" in page and "\"'" in page.split("const esc")[1].split("\n")[0]


def test_the_admin_page_is_told_to_keep_to_itself(tmp_path):
    async def go():
        runner, port = await run(make_central(str(tmp_path / "central.db")))
        try:
            async with aiohttp.ClientSession() as http:
                async with http.get("http://127.0.0.1:%d/admin" % port) as r:
                    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
                    assert "connect-src 'self'" in r.headers["Content-Security-Policy"]
                    assert r.headers["Referrer-Policy"] == "no-referrer" and "ETag" in r.headers
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_looking_for_games_survives_a_shut_port(monkeypatch):
    """Windows tells a UDP socket about a port that was shut as an error on its next read: the rest may still answer."""
    from server import lan
    answers = [ConnectionResetError(10054, "reset"), (json.dumps({"game": "shardsofashen", "name": "Found"}).encode(), ("1.2.3.4", 1))]

    class Sock:
        def __init__(self, *a):
            pass

        def setsockopt(self, *a):
            pass

        def settimeout(self, *a):
            pass

        def sendto(self, *a):
            pass

        def close(self):
            pass

        def recvfrom(self, n):
            if not answers:
                raise socket.timeout()
            got = answers.pop(0)
            if isinstance(got, Exception):
                raise got
            return got
    monkeypatch.setattr(lan.socket, "socket", Sock)
    assert [a["name"] for _, a in lan.find(0.05, to=("127.0.0.1",))] == ["Found"]


def rsa_test_key(bits=640):
    """A small RSA key in a service account's PEM (PKCS#8), made here: bought.py signs Google's JWT with it."""
    import base64
    import random as rnd

    def prime(b):
        while True:
            p = rnd.getrandbits(b) | (1 << (b - 1)) | 1
            if all(pow(a, p - 1, p) == 1 for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)):
                return p
    e = 65537
    while True:
        p, q = prime(bits // 2), prime(bits // 2)
        phi = (p - 1) * (q - 1)
        if p != q and phi % e:
            break
    n, d = p * q, pow(e, -1, phi)

    def item(tag, body):
        size = len(body)
        if size < 128:
            head = bytes([size])
        else:
            k = (size.bit_length() + 7) // 8
            head = bytes([0x80 | k]) + size.to_bytes(k, "big")
        return bytes([tag]) + head + body

    def integer(v):
        return item(0x02, v.to_bytes(v.bit_length() // 8 + 1, "big"))
    pkcs1 = item(0x30, b"".join(integer(v) for v in (0, n, e, d, p, q, d % (p - 1), d % (q - 1), pow(q, -1, p))))
    algo = item(0x30, item(0x06, bytes.fromhex("2a864886f70d010101")) + item(0x05, b""))
    pkcs8 = item(0x30, integer(0) + algo + item(0x04, pkcs1))
    pem = "-----BEGIN PRIVATE KEY-----\n%s\n-----END PRIVATE KEY-----\n" % base64.encodebytes(pkcs8).decode().strip()
    return n, e, d, pem


def rsa_signed(n, e, sig, data):
    """Whether sig is RS256's signature of data by the key (n, e)."""
    import hashlib
    from central import bought
    em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(len(sig), "big")
    return em.startswith(b"\x00\x01\xff") and em.endswith(bought.SHA256_INFO + hashlib.sha256(data).digest())


def test_the_central_server_signs_googles_jwt_itself():
    from central import bought
    n, e, d, pem = rsa_test_key()
    assert bought.rsa_key(pem) == (n, d)
    assert rsa_signed(n, e, bought.rsa_sign((n, d), b"hello"), b"hello")
    assert not rsa_signed(n, e, bought.rsa_sign((n, d), b"hello"), b"hullo")


class PretendStores:
    """Google's token endpoint and Play's purchases, Steam's Web API and itch.io's: what each says of a purchase."""

    def __init__(self, n, e):
        self.n, self.e = n, e
        self.acknowledged = []
        self.play = {"good": {"purchaseState": 0, "acknowledgementState": 0},
                     "refunded": {"purchaseState": 1, "acknowledgementState": 1}}
        self.steam = {"aa11": ("765", "765", True), "bb22": ("766", "765", True), "cc33": ("767", "767", False)}
        self.itch = {"AbC123": {"id": 42, "game_id": 9}}

    def app(self):
        app = web.Application()
        app.router.add_post("/token", self.token)
        app.router.add_route("*", "/play/applications/{pkg}/purchases/products/{product}/tokens/{token}", self.purchase)
        app.router.add_get("/steam/ISteamUserAuth/AuthenticateUserTicket/v1/", self.steam_who)
        app.router.add_get("/steam/ISteamUser/CheckAppOwnership/v4/", self.steam_owns)
        app.router.add_get("/itch/{key}/game/{game}/download_keys", self.itch_key)
        return app

    async def token(self, request):
        import base64
        form = await request.post()
        head, claims, sig = form["assertion"].split(".")

        def unb(t):
            return base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))
        c = json.loads(unb(claims))
        if (not rsa_signed(self.n, self.e, unb(sig), (head + "." + claims).encode())
                or c["iss"] != "play@example.iam.gserviceaccount.com" or "androidpublisher" not in c["scope"]):
            return web.json_response({"error": "invalid_grant"}, status=400)
        return web.json_response({"access_token": "the-access", "expires_in": 3600})

    async def purchase(self, request):
        assert request.headers["Authorization"] == "Bearer the-access"
        token = request.match_info["token"]
        if request.method == "POST" and token.endswith(":acknowledge"):
            self.acknowledged.append(token.split(":")[0])
            return web.json_response({})
        assert request.match_info["product"] == "full_game"
        assert request.match_info["pkg"] == "io.github.kriscs1.shardsofashen"
        if token not in self.play:
            return web.json_response({"error": {"code": 400}}, status=400)
        return web.json_response(self.play[token])

    async def steam_who(self, request):
        q = request.query
        assert q["key"] == "steam-key" and q["appid"] == "480" and q["identity"] == "shardsofashen"
        if q["ticket"] not in self.steam:
            return web.json_response({"response": {"error": {"errorcode": 101}}})
        me, owner, _ = self.steam[q["ticket"]]
        return web.json_response({"response": {"params": {"result": "OK", "steamid": me, "ownersteamid": owner}}})

    async def steam_owns(self, request):
        owns = {me: has for me, _, has in self.steam.values()}
        me = request.query["steamid"]
        return web.json_response({"appownership": {"ownsapp": owns.get(me, False), "ownersteamid": me}})

    async def itch_key(self, request):
        assert request.match_info["key"] == "itch-key" and request.match_info["game"] == "9"
        by_email = {"lee@example.com": {"id": 42, "game_id": 9}, "pal@example.com": {"id": 42, "game_id": 9}}
        found = self.itch.get(request.query.get("download_key", "")) or by_email.get(request.query.get("email", ""))
        return web.json_response({"download_key": found} if found else {"errors": ["invalid download key"]})


def test_owning_the_game_is_checked_with_its_store_and_kept_on_the_account(tmp_path, monkeypatch, confirmed):
    """An account is in the demo till a purchase is checked with its store (Google Play as a service account, Steam's
    ticket and ownership, itch.io's download key): then it has the full game, said with its ticket to a game server.
    One purchase is one account's; a refund or a lent copy doesn't count; a time pass counts while it runs, a few a
    day; an admin can give it or take it back; deleting the account frees its purchases."""
    from central import bought
    admin_of(monkeypatch)
    n, e, _, pem = rsa_test_key()
    key_file = tmp_path / "play.json"
    key_file.write_text(json.dumps({"client_email": "play@example.iam.gserviceaccount.com", "private_key": pem}))
    monkeypatch.setattr(bought, "_play_token", {})
    for name in ("DS_PLAY_SERVICE_ACCOUNT", "DS_STEAM_KEY", "DS_STEAM_APP", "DS_ITCH_KEY", "DS_ITCH_GAME"):
        monkeypatch.delenv(name, raising=False)

    async def go():
        fake = PretendStores(n, e)
        srunner, sport = await run(fake.app())
        s = "http://127.0.0.1:%d" % sport
        monkeypatch.setattr(bought, "TOKEN_URL", s + "/token")
        monkeypatch.setattr(bought, "PLAY_API", s + "/play")
        monkeypatch.setattr(bought, "STEAM_API", s + "/steam")
        monkeypatch.setattr(bought, "ITCH_API", s + "/itch")
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        central = capp[CENTRAL]
        try:
            async with aiohttp.ClientSession() as http:
                async def signup(name, **more):
                    central.signups.clear()
                    return (await post(http, c + "/api/register", {"name": name, **SIGNUP, **more}))["token"]
                boss = await signup("Boss", claim=central.claims["boss"])
                pal, kit, lee = await signup("Pal"), await signup("Kit"), await signup("Lee")

                async def buy(tok, where, **proof):
                    central.fails.clear()
                    return await post(http, c + "/api/buy", {"token": tok, "where": where, "proof": proof})

                monkeypatch.delenv("DS_DEMO", raising=False)
                me = await post(http, c + "/api/account", {"token": pal})
                assert me["full"] is True and me["demo"] is False         # (no demo yet: everyone has all of it)
                monkeypatch.setenv("DS_DEMO", "1")
                me = await post(http, c + "/api/account", {"token": pal})
                assert me["full"] is False and me["bought"] == "" and me["pass_until"] == 0
                # (a store not set up refuses; nothing's taken on the app's word)
                m = await buy(pal, "play", token="good")
                assert not m["ok"] and "can't check" in m["text"]
                assert not (await buy(pal, "nowhere"))["ok"]
                assert not (await post(http, c + "/api/buy", {"token": "nobody", "where": "play"}))["ok"]

                monkeypatch.setenv("DS_PLAY_SERVICE_ACCOUNT", str(key_file))
                m = await buy(pal, "play", token="refunded")
                assert not m["ok"] and "cancelled" in m["text"]
                assert not (await buy(pal, "play", token="made-up"))["ok"]
                m = await buy(pal, "play", token="good")
                assert m["ok"] and m["full"] and m["bought"] == "play"
                assert fake.acknowledged == ["good"]            # (acknowledged: Google doesn't refund it)
                assert (await buy(pal, "play", token="good"))["ok"]                 # (again, a reinstall: still theirs)
                m = await buy(kit, "play", token="good")
                assert not m["ok"] and "another account" in m["text"]
                assert (await post(http, c + "/api/account", {"token": kit}))["full"] is False
                assert not central.store.db.execute("SELECT 1 FROM purchases WHERE ref LIKE '%good%'").fetchone()

                # (Steam: their own copy only)
                monkeypatch.setenv("DS_STEAM_KEY", "steam-key")
                monkeypatch.setenv("DS_STEAM_APP", "480")
                assert "Family Sharing" in (await buy(kit, "steam", ticket="bb22"))["text"]
                assert "doesn't own" in (await buy(kit, "steam", ticket="cc33"))["text"]
                assert not (await buy(kit, "steam", ticket="not hex!"))["ok"]
                assert not (await buy(kit, "steam", ticket="dd44"))["ok"]
                m = await buy(kit, "steam", ticket="aa11")
                assert m["ok"] and m["bought"] == "steam"

                # (itch.io: the purchase page's link, or its key)
                monkeypatch.setenv("DS_ITCH_KEY", "itch-key")
                monkeypatch.setenv("DS_ITCH_GAME", "9")
                assert not (await buy(lee, "itch", key="https://maker.itch.io/ashen/download/Wrong1"))["ok"]
                m = await buy(lee, "itch", key="https://maker.itch.io/ashen/download/AbC123")
                assert m["ok"] and m["bought"] == "itch"
                assert not (await buy(kit, "itch", key="AbC123"))["ok"]     # (Lee's)
                # (bought from the website's Buy: found by the account's confirmed email, never one it sends)
                m = await buy(kit, "itch", by_email=True)
                assert not m["ok"] and "kit@example.com" in m["text"]
                assert not (await buy(kit, "itch", email="lee@example.com"))["ok"]
                assert (await buy(lee, "itch", by_email=True, email="kit@example.com"))["ok"]   # (Lee's own, again)
                assert "another account's" in (await buy(pal, "itch", by_email=True))["text"]  # (the same purchase)
                async with http.get(c + "/api/hello") as r:
                    assert (await r.json())["buy"] is None                  # (no website Buy till it's set)
                monkeypatch.setenv("DS_BUY_URL", "https://maker.itch.io/ashen/purchase")
                monkeypatch.setenv("DS_BUY_PRICE", "$7.99")
                async with http.get(c + "/api/hello") as r:
                    assert (await r.json())["buy"] == {"url": "https://maker.itch.io/ashen/purchase", "price": "$7.99"}

                # (a game server is told with the ticket, and can ask again by the key it was given)
                async def told(tok):
                    t = (await post(http, c + "/api/ticket", {"token": tok, "server": "abc"}))["ticket"]
                    return await post(http, c + "/api/verify", {"ticket": t, "server": "abc"})
                v = await told(pal)
                assert v["ok"] and v["full"] is True and v["pass_until"] == 0
                v = await told(boss)
                assert v["full"] is False
                o = await post(http, c + "/api/game/owns", {"grant": v["grant"]})
                assert o["ok"] and o["name"] == "Boss" and o["full"] is False
                assert not (await post(http, c + "/api/game/owns", {"grant": "made-up"}))["ok"]

                # (a time pass: while it runs, a few a day)
                ends = [central.store.add_pass("Boss", 3600, 3) for _ in range(4)]
                assert ends[3] is None and ends[2] - ends[0] == 7200 and ends[0] > time.time() + 3500
                o = await post(http, c + "/api/game/owns", {"grant": v["grant"]})
                assert o["full"] is True and o["pass_until"] == int(ends[2])
                central.store.db.execute("UPDATE accounts SET pass_until = ? WHERE name = 'Boss'", (time.time() - 1,))
                assert (await post(http, c + "/api/game/owns", {"grant": v["grant"]}))["full"] is False

                # (the admin page: each account's, given or taken back)
                assert not (await post(http, c + "/api/admin/full", {"token": pal, "name": "Pal", "on": True}))["ok"]
                rows = {a["name"]: a for a in (await post(http, c + "/api/admin/accounts", {"token": boss}))["accounts"]}
                assert rows["Pal"]["bought"] == "play" and rows["Kit"]["bought"] == "steam" and rows["Boss"]["bought"] == ""
                assert (await post(http, c + "/api/admin/full", {"token": boss, "name": "Boss", "on": True}))["ok"]
                assert (await post(http, c + "/api/account", {"token": boss}))["bought"] == "admin"
                await post(http, c + "/api/admin/full", {"token": boss, "name": "Pal", "on": False})
                assert (await post(http, c + "/api/account", {"token": pal}))["full"] is False

                # (deleted: its purchases go with it)
                await post(http, c + "/api/admin/delete", {"token": boss, "name": "Lee"})
                assert not central.store.db.execute("SELECT 1 FROM purchases WHERE name = 'Lee'").fetchone()
                assert central.store.owned("Lee") == ("", 0.0, 0.0)
        finally:
            await runner.cleanup()
            await srunner.cleanup()
    asyncio.run(go())


def test_a_time_pass_is_an_ads_reward_signed_by_google(tmp_path, monkeypatch, confirmed):
    """A time pass (the Android app's rewarded ad): the app asks for a key, gives it to the ad, and Google calls back
    once it's watched, signed with one of its keys. Only a reward Google signed counts, once, for that key's account;
    a few a day, an hour each; nothing for one who's bought the game, or with no demo."""
    import secrets
    from urllib.parse import urlencode
    from central import admob
    d = secrets.randbelow(admob.N - 1) + 1
    q = admob.times(d, admob.G)
    monkeypatch.setattr(admob, "_keys", {"keys": {}, "at": 0.0, "tried": 0.0})
    monkeypatch.setenv("DS_DEMO", "1")
    monkeypatch.delenv("DS_ADMOB_REWARDED", raising=False)
    monkeypatch.setenv("DS_PASSES_A_DAY", "2")

    def callback(key, signer=d, key_id="7", unit="5224354917", when=None):
        fields = [("ad_network", "5450213213286189855"), ("ad_unit", unit), ("custom_data", key),
                  ("reward_amount", "1"), ("reward_item", "Hour"),
                  ("timestamp", str(int((when or time.time()) * 1000))), ("transaction_id", secrets.token_hex(8)),
                  ("user_id", "")]
        signed = urlencode(fields)
        sig = admob.sign(signer, signed.encode(), secrets.randbelow(admob.N - 1) + 1)
        return signed + "&signature=" + sig + "&key_id=" + key_id

    async def keys(request):
        pem = "-----BEGIN PUBLIC KEY-----\n%s\n-----END PUBLIC KEY-----" % admob.spki(q)
        return web.json_response({"keys": [{"keyId": 7, "pem": pem, "base64": admob.spki(q)}]})

    async def go():
        gapp = web.Application()
        gapp.router.add_get("/keys.json", keys)
        grunner, gport = await run(gapp)
        monkeypatch.setattr(admob, "KEYS_URL", "http://127.0.0.1:%d/keys.json" % gport)
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        central = capp[CENTRAL]
        try:
            async with aiohttp.ClientSession() as http:
                central.signups.clear()
                tok = (await post(http, c + "/api/register", {"name": "Tess", **SIGNUP}))["token"]
                assert "no time pass" in (await post(http, c + "/api/pass/start", {"token": tok}))["text"]
                monkeypatch.setenv("DS_ADMOB_REWARDED", "ca-app-pub-3940256099942544/5224354917")
                async with http.get(c + "/api/hello") as r:
                    hi = await r.json()
                    assert hi["demo"] is True and hi["demo_level"] == 5
                me = await post(http, c + "/api/account", {"token": tok})
                assert me["full"] is False and me["passes"] == 2
                got = await post(http, c + "/api/pass/start", {"token": tok})
                assert got["ok"] and got["minutes"] == 60 and got["left"] == 2

                async def reward(query):
                    async with http.get(c + "/api/pass/reward?" + query) as r:
                        return r.status
                # (not Google's: a key it doesn't have, another key's signature, an old reward, another game's ad)
                assert await reward(callback(got["key"], key_id="8")) == 400
                assert await reward(callback(got["key"], signer=d + 1)) == 400
                assert await reward(callback(got["key"], when=time.time() - 7200)) == 400
                assert await reward(callback(got["key"], unit="1111")) == 400
                assert await reward(callback(got["key"]).replace("custom_data=", "custom_data=x")) == 400
                assert (await post(http, c + "/api/account", {"token": tok}))["full"] is False
                # (Google's: an hour, and only once for its key)
                assert await reward(callback(got["key"])) == 200
                me = await post(http, c + "/api/account", {"token": tok})
                assert me["full"] is True and me["pass_until"] > time.time() + 3500 and me["passes"] == 1
                assert await reward(callback(got["key"])) == 200        # (Google trying again: thanked, not counted)
                assert central.store.passes_today("Tess") == 1
                assert await reward(callback("made-up")) == 200
                # (a few a day)
                again = await post(http, c + "/api/pass/start", {"token": tok})
                assert await reward(callback(again["key"])) == 200
                me = await post(http, c + "/api/account", {"token": tok})
                assert me["passes"] == 0 and me["pass_until"] > time.time() + 7100
                assert "tomorrow" in (await post(http, c + "/api/pass/start", {"token": tok}))["text"]
                # (bought: none)
                central.store.set_full("Tess", "play")
                assert "already" in (await post(http, c + "/api/pass/start", {"token": tok}))["text"]
                assert (await post(http, c + "/api/account", {"token": tok}))["passes"] == 0
                assert not (await post(http, c + "/api/pass/start", {"token": "nobody"}))["ok"]
        finally:
            await runner.cleanup()
            await grunner.cleanup()
    asyncio.run(go())


def test_a_time_pass_needs_play_integritys_word_that_its_the_real_app_on_a_real_phone(tmp_path, monkeypatch, confirmed):
    """With DS_PLAY_INTEGRITY=1, a time pass's key comes only after Play Integrity's verdict, decoded by Google with
    the service account: the nonce it was given, just now, this game from Google Play on a phone that passes. An
    emulator, a rooted phone or a tampered app gets none (ads farmed by a machine would cost the AdMob account)."""
    from central import bought
    n, e, _, pem = rsa_test_key()
    key_file = tmp_path / "play.json"
    key_file.write_text(json.dumps({"client_email": "play@example.iam.gserviceaccount.com", "private_key": pem}))
    monkeypatch.setattr(bought, "_play_token", {})
    monkeypatch.setenv("DS_PLAY_SERVICE_ACCOUNT", str(key_file))
    monkeypatch.setenv("DS_PLAY_INTEGRITY", "1")
    monkeypatch.setenv("DS_DEMO", "1")
    monkeypatch.setenv("DS_ADMOB_REWARDED", "ca-app-pub-3940256099942544/5224354917")
    scopes = []

    async def token(request):
        scopes.append(json.loads(base64.urlsafe_b64decode((await request.post())["assertion"].split(".")[1] + "=="))
                      ["scope"])
        return web.json_response({"access_token": "t", "expires_in": 3600})

    async def decode(request):
        if request.headers.get("Authorization") != "Bearer t" or                 request.match_info["rest"] != "io.github.kriscs1.shardsofashen:decodeIntegrityToken":
            return web.json_response({}, status=403)
        made = (await request.json())["integrity_token"]
        return web.json_response({"tokenPayloadExternal": json.loads(made)} if made.startswith("{") else {},
                                 status=200 if made.startswith("{") else 400)

    def verdict(nonce, app="PLAY_RECOGNIZED", device=("MEETS_DEVICE_INTEGRITY",), when=None, package=None):
        return json.dumps({
            "requestDetails": {"requestPackageName": package or "io.github.kriscs1.shardsofashen", "nonce": nonce,
                               "timestampMillis": str(int((when or time.time()) * 1000))},
            "appIntegrity": {"appRecognitionVerdict": app}, "deviceIntegrity": {"deviceRecognitionVerdict": list(device)}})

    async def go():
        gapp = web.Application()
        gapp.router.add_post("/token", token)
        gapp.router.add_post("/integrity/{rest}", decode)
        grunner, gport = await run(gapp)
        g = "http://127.0.0.1:%d" % gport
        monkeypatch.setattr(bought, "TOKEN_URL", g + "/token")
        monkeypatch.setattr(bought, "INTEGRITY_API", g + "/integrity")
        capp = make_central(str(tmp_path / "central.db"))
        runner, port = await run(capp)
        c = "http://127.0.0.1:%d" % port
        central = capp[CENTRAL]
        try:
            async with aiohttp.ClientSession() as http:
                central.signups.clear()
                tok = (await post(http, c + "/api/register", {"name": "Tess", **SIGNUP}))["token"]

                async def start(**more):
                    return await post(http, c + "/api/pass/start", {"token": tok, **more})
                asked = await start()
                assert not asked["ok"] and asked["integrity"] and "key" not in asked      # (first, the verdict)
                for bad, words in ((verdict("another"), "wasn't this one"),
                                   (verdict(None, package="com.someone.else"), "wasn't this one"),
                                   (verdict(None, when=time.time() - 3600), "wasn't this one"),
                                   (verdict(None, app="UNRECOGNIZED_VERSION"), "isn't the one from Google Play"),
                                   (verdict(None, device=()), "passes Google Play's checks"),
                                   (verdict(None, device=("MEETS_BASIC_INTEGRITY",)), "passes Google Play's checks"),
                                   ("not-a-token", "couldn't show")):
                    nonce = (await start())["integrity"]
                    got = await start(integrity=bad.replace("null", json.dumps(nonce)))
                    assert not got["ok"] and words in got["text"] and "key" not in got, (bad, got)
                nonce = (await start())["integrity"]
                got = await start(integrity=verdict(nonce))
                assert got["ok"] and got["key"] and got["left"] == 3                # (the real app, on a real phone)
                again = await start(integrity=verdict(nonce))
                assert not again["ok"] and again["integrity"]                       # (a verdict's good once)
                assert set(scopes) == {bought.INTEGRITY_SCOPE}
                monkeypatch.setenv("DS_PLAY_INTEGRITY", "")
                assert (await start())["ok"]                                        # (off: as before)
        finally:
            await runner.cleanup()
            await grunner.cleanup()
    asyncio.run(go())
