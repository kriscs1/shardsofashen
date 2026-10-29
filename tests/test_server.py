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


async def start(db, max_players=5, admins=""):
    app = make_app(ROOT, db, max_players, admins=admins)
    runner = web.AppRunner(app)
    await runner.setup()
    port = free_port()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    return runner, app, "ws://127.0.0.1:%d/ws" % port


async def login(http, url, name, password, mode="register", **more):
    ws = await http.ws_connect(url)
    await ws.send_json({"t": mode, "name": name, "password": password, **more})
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
            h = game.world.homes.create("Saver")
            h["visit"] = "open"
            m = game.world.homes.map_of("Saver")
            game.world.change_tile(m, 5, 5, "Timber001")
            h["cells"]["5,5"] = {"tile": "Timber001"}
            farm = game.world.maps["3,3,0"]
            game.world.farms.sow(farm, 5, 14, "Potato", "Saver")
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
        homes = game.world.homes
        assert homes.home_of("Saver")["visit"] == "open"
        m = homes.map_of("Saver")
        assert m is not None and m.tile[m.cell(5, 5)] == "Timber001"
        farm = game.world.maps["3,3,0"]
        assert game.world.farms.plots[("3,3,0", 5, 14)]["owner"] == "Saver"
        assert farm.decor[farm.cell(5, 14)].startswith("Potato_Crop")
        await runner.cleanup()

    asyncio.run(first())
    asyncio.run(second())


async def chats(ws, seconds=1.0):
    out = []
    end = asyncio.get_event_loop().time() + seconds
    while True:
        left = end - asyncio.get_event_loop().time()
        if left <= 0:
            return out
        try:
            msg = await asyncio.wait_for(ws.receive(), left)
        except asyncio.TimeoutError:
            return out
        if msg.type != aiohttp.WSMsgType.TEXT:
            return out
        data = json.loads(msg.data)
        out += [m for m in (data if isinstance(data, list) else [data]) if m.get("t") == "chat"]


def test_chat_and_whispers(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "c.db"))
        async with aiohttp.ClientSession() as http:
            a, _ = await login(http, url, "Anna Lee", "pw12")
            b, _ = await login(http, url, "Bo", "pw12")
            c, _ = await login(http, url, "Cy", "pw12")
            await chats(a, 0.3), await chats(b, 0.3), await chats(c, 0.3)
            await a.send_json({"t": "chat", "text": "/w Bo psst"})
            got_b, got_c = await chats(b), await chats(c)
            assert any(m.get("whisper") == "from" and m["text"] == "psst" and m["from"] == "Anna Lee" for m in got_b)
            assert not any(m.get("text") == "psst" for m in got_c)          # only Bo hears it
            await b.send_json({"t": "chat", "text": "/r hi back"})
            got_a = await chats(a)
            assert any(m.get("whisper") == "from" and m["text"] == "hi back" for m in got_a)
            await c.send_json({"t": "chat", "text": "/w Anna Lee hello"})  # (a name with a space)
            assert any(m.get("text") == "hello" for m in await chats(a))
            await c.send_json({"t": "chat", "text": "hello all"})
            assert any(m.get("text") == "hello all" and not m.get("whisper") for m in await chats(b))
        await runner.cleanup()
    asyncio.run(run())


def test_admins_from_the_server_settings(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "a.db"), admins="Kris, ann")
        async with aiohttp.ClientSession() as http:
            _, m = await login(http, url, "Kris", "pw12")
            assert m["t"] == "welcome" and m["admin"] is True
            _, m = await login(http, url, "Ann", "pw12")                # (names in any case)
            assert m["admin"] is True
            _, m = await login(http, url, "Bob", "pw12")
            assert m["admin"] is False
        await runner.cleanup()
    asyncio.run(run())


def test_the_version_is_on_the_login_screen(tmp_path, monkeypatch):
    from server.version import version_info
    monkeypatch.setenv("DS_BUILD", "57")
    monkeypatch.setenv("DS_COMMIT", "abcdef123")
    monkeypatch.setenv("DS_BUILD_DATE", "2026-10-23")
    base = open(os.path.join(ROOT, "VERSION")).read().strip()
    assert version_info(ROOT) == {"version": base + ".57", "commit": "abcdef1", "date": "2026-10-23"}

    async def run():
        runner, app, url = await start(str(tmp_path / "v.db"))
        async with aiohttp.ClientSession() as http:
            ws = await http.ws_connect(url)
            msg = await asyncio.wait_for(ws.receive(), 10)
            data = json.loads(msg.data)
            hello = next(m for m in (data if isinstance(data, list) else [data]) if m["t"] == "hello")
            assert hello["version"] == base + ".57" and hello["date"] == "2026-10-23"
            manifest = os.path.join(ROOT, "web", "assets", "manifest.json")
            if os.path.exists(manifest):                               # (a page from before an update loads again)
                with open(manifest, encoding="utf-8") as f:
                    assert hello["assets"] == json.load(f)["version"]
            else:
                assert hello["assets"] == ""                           # (no assets made yet: GitHub's tests, before the image)
            async with http.get(url.replace("ws://", "http://").replace("/ws", "/health")) as r:
                assert (await r.json())["version"] == base + ".57"
            await ws.close()
        await runner.cleanup()
    asyncio.run(run())


async def wait_for(ws, kind, seconds=5.0):
    end = asyncio.get_event_loop().time() + seconds
    while True:
        left = end - asyncio.get_event_loop().time()
        if left <= 0:
            return None
        try:
            msg = await asyncio.wait_for(ws.receive(), left)
        except asyncio.TimeoutError:
            return None
        if msg.type != aiohttp.WSMsgType.TEXT:
            return None
        data = json.loads(msg.data)
        for m in data if isinstance(data, list) else [data]:
            if m.get("t") == kind:
                return m


def test_changing_and_resetting_passwords(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "p.db"), admins="Boss")
        async with aiohttp.ClientSession() as http:
            ws, _ = await login(http, url, "Player", "oldpass")
            await ws.send_json({"t": "password", "old": "wrong", "new": "newpass"})
            m = await wait_for(ws, "password_result")
            assert m and not m["ok"]                                   # (not without the current one)
            await ws.send_json({"t": "password", "old": "oldpass", "new": "newpass"})
            m = await wait_for(ws, "password_result")
            assert m and m["ok"]
            await ws.close()
            _, m = await login(http, url, "Player", "oldpass", mode="login")
            assert m["t"] == "login_fail"
            ws, m = await login(http, url, "Player", "newpass", mode="login")
            assert m["t"] == "welcome"
            await ws.close()
            boss, _ = await login(http, url, "Boss", "bosspass")
            await boss.send_json({"t": "admin_password", "name": "Player", "new": "fresh1"})
            m = await wait_for(boss, "admin_status")
            assert m and "Player's password is set" in m["text"]
            await boss.close()
            _, m = await login(http, url, "Player", "fresh1", mode="login")
            assert m["t"] == "welcome"
            nobody, _ = await login(http, url, "Nobody", "pass1")       # (not an admin: ignored)
            await nobody.send_json({"t": "admin_password", "name": "Player", "new": "hacked"})
            await asyncio.sleep(0.5)
            await nobody.close()
            _, m = await login(http, url, "Player", "hacked", mode="login")
            assert m["t"] == "login_fail"
        await runner.cleanup()
    asyncio.run(run())


def test_a_password_every_time(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "r.db"))
        async with aiohttp.ClientSession() as http:
            ws, m = await login(http, url, "Keeper", "pass1", remember=True)
            assert m["t"] == "welcome" and "token" not in m             # (nothing to log in with but the password)
            await ws.close()
            _, m = await login(http, url, "Keeper", "", mode="login", token="anything")
            assert m["t"] == "login_fail"
            ws, m = await login(http, url, "Keeper", "pass1", mode="login")
            assert m["t"] == "welcome"
            await ws.close()
        await runner.cleanup()
    asyncio.run(run())

def test_everyone_sees_where_the_others_are(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "w.db"))
        async with aiohttp.ClientSession() as http:
            one, _ = await login(http, url, "Finder", "pass1")
            two, _ = await login(http, url, "Found", "pass2")
            seen = None
            for _ in range(3):
                m = await wait_for(one, "where", seconds=3)
                if m and any(p["name"] == "Found" for p in m["list"]):
                    seen = next(p for p in m["list"] if p["name"] == "Found")
                    break
            assert seen and {"x", "y", "z"} <= set(seen)
            await one.close()
            await two.close()
        await runner.cleanup()
    asyncio.run(run())


def test_too_many_wrong_passwords_wait(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "t.db"))
        try:
            async with aiohttp.ClientSession() as http:
                w, m = await login(http, url, "Guarded", "right-one")
                assert m["t"] == "welcome"
                await w.close()
                reasons = []
                for _ in range(6):
                    w, m = await login(http, url, "Guarded", "wrong", mode="login")
                    reasons.append(m.get("reason", ""))
                    await w.close()
                assert reasons[:5] == ["Wrong password."] * 5
                assert "Too many wrong passwords" in reasons[5]
                w, m = await login(http, url, "Guarded", "right-one", mode="login")
                assert m["t"] == "login_fail" and "Too many" in m["reason"]     # (even the right one, for a while)
                await w.close()
        finally:
            await runner.cleanup()
    asyncio.run(run())


def test_a_game_on_the_network_answers_who_is_there(tmp_path, monkeypatch):
    from server import lan
    lan_port = free_port()
    monkeypatch.setenv("DS_LAN_PORT", str(lan_port))

    async def run():
        runner, app, url = await start(str(tmp_path / "a.db"))
        base = url.replace("ws://", "http://").replace("/ws", "")
        found = await asyncio.get_running_loop().run_in_executor(None, lambda: lan.find(1.0, lan_port, ("127.0.0.1",)))
        assert len(found) == 1
        address, answer = found[0]
        assert address == "127.0.0.1" and answer["game"] == "shardsofashen" and answer["max"] == 5
        async with aiohttp.ClientSession() as http:
            async with http.get(base + "/manifest.webmanifest") as r:
                assert r.status == 200 and json.loads(await r.text())["display"] == "fullscreen"
        await runner.cleanup()
    asyncio.run(run())


def test_a_database_under_the_old_name_carries_on_under_the_new_one(tmp_path):
    old = Store(str(tmp_path / "dragonsword.db"))
    old.create_account("Keeper", "x")
    old.close()
    new = Store(str(tmp_path / "ashen.db"))                         # (the game's name everywhere now)
    assert new.account("Keeper") is not None
    assert not os.path.exists(tmp_path / "dragonsword.db") and os.path.exists(tmp_path / "ashen.db")
    new.close()
    fresh = Store(str(tmp_path / "other" / "ashen.db"))             # (nothing old beside it: a new one)
    assert fresh.account("Keeper") is None
    fresh.close()
