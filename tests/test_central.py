"""The central server: accounts, tickets into a game server, the remote servers list."""
import asyncio
import json
import socket

import aiohttp
from aiohttp import web

from central.app import make_central
from server.app import make_app, GAME
from tests.test_server import ROOT, login


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


async def ticket_in(http, url, ticket):
    ws = await http.ws_connect(url)
    await ws.send_json({"t": "ticket", "ticket": ticket})
    while True:
        data = json.loads((await asyncio.wait_for(ws.receive(), 10)).data)
        for m in data if isinstance(data, list) else [data]:
            if m["t"] in ("welcome", "login_fail"):
                return ws, m


def test_one_account_for_every_game_and_the_remote_list(tmp_path, monkeypatch):
    async def go():
        crunner, cport = await run(make_central(str(tmp_path / "central.db")))
        central = "http://127.0.0.1:%d" % cport
        monkeypatch.setenv("DS_CENTRAL", central)
        monkeypatch.setenv("DS_PUBLIC", "1")
        monkeypatch.setenv("DS_PUBLIC_URL", "https://play.example.com")
        gapp = make_app(ROOT, str(tmp_path / "game.db"), 5, name="Kris's World")
        grunner, gport = await run(gapp)
        game = gapp[GAME]
        wsurl = "ws://127.0.0.1:%d/ws" % gport
        try:
            async with aiohttp.ClientSession() as http:
                for _ in range(40):                                     # (it announces itself as it starts)
                    await asyncio.sleep(0.1)
                    listed = await (await http.get(central + "/api/servers")).json()
                    if listed:
                        break
                assert listed and listed[0]["key"] == game.server_id() and listed[0]["name"] == "Kris's World"
                assert listed[0]["url"] == "https://play.example.com"
                info = await (await http.get("http://127.0.0.1:%d/api/info" % gport)).json()
                assert info["id"] == game.server_id()

                r = await post(http, central + "/api/register", {"name": "Wanderer", "password": "longpassword"})
                assert r["ok"] and r["token"] and len(r["recovery"]) == 19
                token = r["token"]
                assert (await post(http, central + "/api/me", {"token": token}))["name"] == "Wanderer"
                t = await post(http, central + "/api/ticket", {"token": token, "server": game.server_id()})
                ws, m = await ticket_in(http, wsurl, t["ticket"])
                assert m["t"] == "welcome" and m["name"] == "Wanderer"     # (a character here, made by the ticket)
                await ws.close()
                ws, m = await ticket_in(http, wsurl, t["ticket"])
                assert m["t"] == "login_fail"                               # (a ticket's good once)
                await ws.close()
                other = await post(http, central + "/api/ticket", {"token": token, "server": "0123456789abcdef"})
                ws, m = await ticket_in(http, wsurl, other["ticket"])
                assert m["t"] == "login_fail"                               # (made out to another server)
                await ws.close()

                # (a character this server had of its own first: its password links it)
                local, _ = await login(http, wsurl, "Oldtimer", "localpass1")
                await local.close()
                r = await post(http, central + "/api/register", {"name": "Oldtimer", "password": "longpassword"})
                t = await post(http, central + "/api/ticket", {"token": r["token"], "server": game.server_id()})
                ws = await http.ws_connect(wsurl)
                await ws.send_json({"t": "ticket", "ticket": t["ticket"]})
                got = None
                while got is None:
                    data = json.loads((await asyncio.wait_for(ws.receive(), 10)).data)
                    got = next((x for x in (data if isinstance(data, list) else [data]) if x["t"] == "login_fail"), None)
                assert "of its own" in got["reason"]
                await ws.send_json({"t": "login", "name": "Oldtimer", "password": "localpass1"})
                while True:
                    data = json.loads((await asyncio.wait_for(ws.receive(), 10)).data)
                    if any(x["t"] == "welcome" for x in (data if isinstance(data, list) else [data])):
                        break
                await ws.close()
                t = await post(http, central + "/api/ticket", {"token": r["token"], "server": game.server_id()})
                ws, m = await ticket_in(http, wsurl, t["ticket"])
                assert m["t"] == "welcome" and m["name"] == "Oldtimer"     # (linked: in by ticket now)
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
