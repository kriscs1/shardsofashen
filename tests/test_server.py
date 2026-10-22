"""The server: accounts, the player limit, saving and loading the world."""
import asyncio
import json
import os
import socket

import aiohttp
import pytest
from aiohttp import web

from server.app import make_app, GAME
from server.store import Store
from server import auth

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def start(db, max_players=5):
    app = make_app(ROOT, db, max_players)
    runner = web.AppRunner(app)
    await runner.setup()
    port = free_port()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    return runner, app, "ws://127.0.0.1:%d/ws" % port


async def login(http, url, name, password, mode="register"):
    ws = await http.ws_connect(url)
    await ws.send_json({"t": mode, "name": name, "password": password})
    while True:
        msg = await asyncio.wait_for(ws.receive(), 10)
        data = json.loads(msg.data)
        for m in data if isinstance(data, list) else [data]:
            if m["t"] in ("welcome", "login_fail"):
                return ws, m


def test_passwords():
    h = auth.hash_password("secret")
    assert auth.check_password("secret", h)
    assert not auth.check_password("wrong", h)
    assert auth.clean_name("Bob <script>") == "Bob script"


def test_login_limit_and_passwords(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "t.db"), max_players=2)
        try:
            async with aiohttp.ClientSession() as http:
                w1, m1 = await login(http, url, "One", "pass1")
                assert m1["t"] == "welcome"
                w2, m2 = await login(http, url, "Two", "pass2")
                assert m2["t"] == "welcome"
                w3, m3 = await login(http, url, "Three", "pass3")
                assert m3["t"] == "login_fail" and "full" in m3["reason"]
                await w3.close()
                await w2.close()
                await asyncio.sleep(0.3)
                w4, m4 = await login(http, url, "One", "wrong", "login")
                assert m4["t"] == "login_fail"          # (One is still on; a wrong password is refused anyway)
                await w4.close()
                w5, m5 = await login(http, url, "Two", "pass2", "login")
                assert m5["t"] == "welcome"
                for w in (w1, w5):
                    await w.close()
        finally:
            await runner.cleanup()
    asyncio.run(run())


def test_world_survives_a_restart(tmp_path):
    db = str(tmp_path / "w.db")

    async def first():
        runner, app, url = await start(db)
        game = app[GAME]
        game.world.add_action_to_queue("ADD", "Test_Thing", "MapItem", "1", "1,1,0", "100,100", 3600)
        game.world.set_day_fraction(0.6)
        async with aiohttp.ClientSession() as http:
            ws, m = await login(http, url, "Saver", "pw12")
            assert m["t"] == "welcome"
            s = game.world.sessions["Saver"]
            s.add_inventory_item("Logs", 5, quiet=True)
            await ws.close()
            await asyncio.sleep(0.3)
        await runner.cleanup()

    async def second():
        runner, app, url = await start(db)
        game = app[GAME]
        assert any("Test_Thing" in q for q in game.world.action_queue)
        assert abs(game.world.day_fraction() - 0.6) < 0.02
        st = Store(db).load_character("Saver")
        assert any(i[0] == "Logs" and i[1] >= 5 for i in st["inventory"])
        await runner.cleanup()

    asyncio.run(first())
    asyncio.run(second())
