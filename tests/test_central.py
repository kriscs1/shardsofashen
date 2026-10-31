"""The central server: accounts, tickets into a game server, the remote servers list."""
import asyncio
import json
import socket

import aiohttp
from aiohttp import web

from central.app import make_central
from server.app import make_app, GAME
from tests.test_server import ROOT, come_in, device_of, replies


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


def test_one_account_for_every_game_and_the_remote_list(tmp_path, monkeypatch):
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
                r = await post(http, central + "/api/register", {"name": "Wanderer", "password": "longpassword"})
                assert r["ok"] and r["token"] and len(r["recovery"]) == 19
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

                # (a character this server had of its own first: its password brings it in, once)
                from server import auth
                game.store.create_account("Oldtimer", auth.hash_password("localpass1"))
                r = await post(http, central + "/api/register", {"name": "Oldtimer", "password": "longpassword"})
                t = await post(http, central + "/api/ticket", {"token": r["token"], "server": game.server_id(),
                                                               "url": here})
                ws, m = await come_in(http, wsurl, device_of("old"), ticket=t["ticket"])
                assert m["account"] == "Oldtimer" and m["list"] == [] and m["old"]
                await ws.send_json({"t": "claim", "name": "Oldtimer", "password": "localpass1"})
                m = await replies(ws, ("characters", "login_fail"))
                assert [c["name"] for c in m["list"]] == ["Oldtimer"]
                await ws.close()
                t = await post(http, central + "/api/ticket", {"token": r["token"], "server": game.server_id(),
                                                               "url": here})
                ws, m = await ticket_in(http, wsurl, t["ticket"], "Oldtimer")
                assert m["t"] == "welcome" and m["name"] == "Oldtimer" and m["account"] == "Oldtimer"
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
                assert not (await post(http, c + "/api/register", {"name": "Mail", "password": "longpassword",
                                                                    "email": "not an email"}))["ok"]
                r = await post(http, c + "/api/register", {"name": "Mail", "password": "longpassword",
                                                            "email": "mail@example.com"})
                assert r["ok"]
                r = await post(http, c + "/api/forgot", {"who": "mail@example.com"})
                assert r["ok"] and len(mail.SENT) == 1 and mail.SENT[0][0] == "mail@example.com"
                code = [w for w in mail.SENT[0][2].split() if "-" in w and len(w) == 9][0]
                assert not (await post(http, c + "/api/reset", {"name": "Mail", "code": "AAAA-BBBB",
                                                                 "password": "newpassword1"}))["ok"]
                r = await post(http, c + "/api/reset", {"name": "mail@example.com", "code": code,
                                                         "password": "newpassword1"})
                assert r["ok"] and r["recovery"]
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

                squat = await post(http, c + "/api/register", {"name": "Boss", "password": "longpassword"})
                assert not squat["ok"] and squat["claim"]       # (an admin's name: only with the code from the log)
                boss = (await post(http, c + "/api/register", {"name": "Boss", "password": "longpassword",
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
