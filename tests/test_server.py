"""The server: who's playing and their characters, the player limit, saving and loading the world."""
import asyncio
import json
import os
import socket
import time
from types import SimpleNamespace

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


async def start(db, max_players=5, admins="", own=False):
    app = make_app(ROOT, db, max_players, admins=admins, own=own)
    runner = web.AppRunner(app)
    await runner.setup()
    port = free_port()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    return runner, app, "ws://127.0.0.1:%d/ws" % port


def device_of(name):
    return ("device of " + name).ljust(16, ".")


async def replies(ws, kinds):
    while True:
        msg = await asyncio.wait_for(ws.receive(), 10)
        data = json.loads(msg.data)
        for m in data if isinstance(data, list) else [data]:
            if m["t"] in kinds:
                return m


async def login(http, url, name, password="", mode="register", device=None, headers=None, auth_with=None, **more):
    """In as a device of its own (each name its own device, unless device is given; auth_with: a ticket, the host's
    key...), then a new character (register) or one of theirs (login). (password: the old tests'; nobody needs one.)"""
    ws = await http.ws_connect(url, headers=headers or {})
    await ws.send_json({"t": "auth", "device": device or device_of(name), **(auth_with or {})})
    m = await replies(ws, ("characters", "login_fail"))
    if m["t"] == "login_fail":
        return ws, m
    await ws.send_json({"t": "create" if mode == "register" else "play", "name": name, **more})
    return ws, await replies(ws, ("welcome", "login_fail"))


async def come_in(http, url, device, **more):
    """In as someone, no further: their characters (or why not)."""
    ws = await http.ws_connect(url, headers=more.pop("headers", {}))
    await ws.send_json({"t": "auth", "device": device, **more})
    return ws, await replies(ws, ("characters", "login_fail"))


def test_passwords():
    h = auth.hash_password("secret")
    assert auth.check_password("secret", h)
    assert not auth.check_password("wrong", h)
    assert auth.clean_name("Bob <script>") == "Bob script"


def test_the_player_limit_and_whose_characters(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "t.db"), max_players=2)
        try:
            async with aiohttp.ClientSession() as http:
                w1, m1 = await login(http, url, "One")
                assert m1["t"] == "welcome"
                w2, m2 = await login(http, url, "Two")
                assert m2["t"] == "welcome"
                w3, m3 = await login(http, url, "Three")
                assert m3["t"] == "login_fail" and "full" in m3["reason"]
                await w3.close()
                await w2.close()
                await asyncio.sleep(0.3)
                w4, m4 = await login(http, url, "One", mode="login", device=device_of("Two"))
                assert m4["t"] == "login_fail" and "isn't one of your" in m4["reason"]    # (someone else's)
                await w4.close()
                w5, m5 = await login(http, url, "Two", mode="login")
                assert m5["t"] == "welcome"
                for w in (w1, w5):
                    await w.close()
        finally:
            await runner.cleanup()
    asyncio.run(run())


def test_everyone_and_the_world_are_saved_together(tmp_path):
    """A save is everyone online and the world in one go: a trade's two sides can't be saved apart."""
    db = str(tmp_path / "j.db")

    async def run():
        runner, app, url = await start(db)
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                a, _ = await login(http, url, "Giver", "pw12")
                b, _ = await login(http, url, "Taker", "pw12")
                game.world.sessions["Taker"].add_inventory_item("Logs", 7, quiet=True)
                game.world.add_action_to_queue("ADD", "Joint_Thing", "MapItem", "1", "1,1,0", "100,100", 3600)
                await a.close()                     # (one leaves: the other, and the world, are saved with them)
                await asyncio.sleep(0.3)
                st = Store(db)
                assert any(i[0] == "Logs" and i[1] >= 7 for i in st.load_character("Taker")["inventory"])
                assert any("Joint_Thing" in q for q in st.load_world()["queue"])
                await b.close()
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


def test_admins_from_the_server_settings(tmp_path, monkeypatch):
    """DS_ADMINS names Hallisium accounts (proved by a ticket, or the host's key), never a character's name."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def run():
        runner, app, url = await start(str(tmp_path / "a.db"), admins="Kris, ann")
        async with aiohttp.ClientSession() as http:
            host = lambda account: {"host": "the-hosts-own-key", "account": account}      # noqa: E731
            _, m = await login(http, url, "Kristoff", auth_with=host("Kris"))
            assert m["t"] == "welcome" and m["admin"] is True and m["account"] == "Kris"
            _, m = await login(http, url, "Annie", auth_with=host("ANN"))     # (accounts in any case)
            assert m["admin"] is True
            _, m = await login(http, url, "Kris")                              # (a device's character called Kris)
            assert m["t"] == "welcome" and m["admin"] is False
            _, m = await login(http, url, "Sly", auth_with={"host": "a-guess", "account": "Kris"})
            assert m["admin"] is False and m["account"] == ""                  # (the wrong key: only a device)
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


def test_an_unknown_proxy_is_not_the_local_network(tmp_path, monkeypatch):
    """Coming through a reverse proxy nobody declared looks like the local network (the connection's from the proxy):
    it mustn't count as that. Declared, the proxy's word goes, but never that it's passing on this machine."""
    def addr(remote, **headers):
        return auth.client_address(SimpleNamespace(remote=remote, headers=headers))
    outside = {"X-Forwarded-For": "8.8.8.8"}
    assert addr("192.168.1.5") == "192.168.1.5"
    assert addr("192.168.1.5", **outside) == "proxied:8.8.8.8"
    assert addr("192.168.1.5", **{"X-Real-IP": "8.8.8.8"}) == "proxied:8.8.8.8"
    assert addr("8.8.4.4", **outside) == "8.8.4.4"                              # (straight from the world: no say)
    monkeypatch.setenv("DS_TRUST_PROXY", "1")
    assert addr("172.18.0.2", **outside) == "8.8.8.8"
    assert addr("172.18.0.2", **{"X-Forwarded-For": "1.2.3.4, 192.168.1.9"}) == "192.168.1.9"
    assert addr("172.18.0.2", **{"X-Forwarded-For": "127.0.0.1"}) == "proxied:127.0.0.1"   # (nobody is this machine)
    assert addr("172.18.0.2", **{"X-Real-IP": "8.8.8.8"}) == "proxied:8.8.8.8"
    monkeypatch.delenv("DS_TRUST_PROXY")

    async def run():
        monkeypatch.setenv("DS_CENTRAL", "http://127.0.0.1:9")                  # (joined to one: no ticket is asked of it)
        runner, app, url = await start(str(tmp_path / "t.db"), own=True)
        try:
            async with aiohttp.ClientSession() as http:
                app[GAME].store.set_setting("lan_open", "1")
                _, m = await come_in(http, url, device_of("Lan"))
                assert m["t"] == "characters"                                   # (this machine: a device's key will do)
                _, m = await come_in(http, url, device_of("Far"), headers=outside)
                assert m["t"] == "login_fail" and "Sign in" in m["reason"]
        finally:
            await runner.cleanup()
    asyncio.run(run())


def test_a_page_is_told_the_code_it_should_be_running(tmp_path, monkeypatch):
    """The hello says the page's code (a page from other code loads again) and where the start screen is."""
    async def run():
        monkeypatch.setenv("DS_CENTRAL", "https://central.example.com/")
        runner, app, url = await start(str(tmp_path / "t.db"))
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                ws = await http.ws_connect(url)
                hello = await replies(ws, ("hello",))
                assert hello["code"] == game.code_version() and len(hello["code"]) == 12
                assert hello["home"] == "https://central.example.com"
                await ws.close()
        finally:
            await runner.cleanup()
    asyncio.run(run())


def test_a_device_keeps_its_own_characters(tmp_path, monkeypatch):
    """A device's key (no Hallisium account) has its characters here, at most MOST_CHARACTERS; names are one of a kind on
    the server; a device's key alone does on this machine and its network, never from the internet or on a public
    server."""
    from server.game import MOST_CHARACTERS
    monkeypatch.setenv("DS_REGISTER_PER_DAY", "0")         # (no day's limit: they all come from this machine)

    async def run():
        runner, app, url = await start(str(tmp_path / "r.db"))
        try:
            async with aiohttp.ClientSession() as http:
                ws, m = await login(http, url, "Keeper")
                assert m["t"] == "welcome" and m["account"] == ""
                await ws.close()
                await asyncio.sleep(0.3)
                ws, m = await come_in(http, url, device_of("Keeper"))           # (again, a reload: still theirs)
                assert [(c["name"], c["level"]) for c in m["list"]] == [("Keeper", 1)] and "look" in m["list"][0]
                await ws.close()
                ws, m = await come_in(http, url, device_of("Another"))
                assert m["list"] == []
                await ws.send_json({"t": "create", "name": "keeper"})
                m = await replies(ws, ("welcome", "login_fail"))
                assert m["t"] == "login_fail" and "already" in m["reason"]      # (one of a kind here, any case)
                await ws.close()
                for k in range(MOST_CHARACTERS):
                    w, m = await login(http, url, "Many%d" % k, device=device_of("Many"))
                    assert m["t"] == "welcome"
                    await w.close()
                _, m = await login(http, url, "Too Many", device=device_of("Many"))
                assert m["t"] == "login_fail" and "the most" in m["reason"]
                _, m = await come_in(http, url, "short")
                assert m["t"] == "login_fail" and "Sign in" in m["reason"]
        finally:
            await runner.cleanup()
    asyncio.run(run())
    game_addr = __import__("server.game", fromlist=["GameServer"]).GameServer
    g = game_addr.__new__(game_addr)
    assert g.devices_welcome("8.8.8.8")                                         # (no central server: no other way)
    monkeypatch.setenv("DS_CENTRAL", "https://central.example.com")
    assert not g.devices_welcome("192.168.1.20") and not g.devices_welcome("127.0.0.1")     # (a remote server: accounts only)
    g.own = True                                                                # (an app's own game: its network's)
    assert g.devices_welcome("127.0.0.1") and g.devices_welcome("192.168.1.20") and g.devices_welcome("::1")
    assert not g.devices_welcome("8.8.8.8") and not g.devices_welcome("")


def test_the_host_and_an_account_need_no_network(tmp_path, monkeypatch):
    """The app's own game lets its host in by the key it was started with, as their account, no central server; the
    device that came in by an account (a ticket, or the host's key) is that account's here from then on, so a reload,
    or the central server away, is still them."""
    db = str(tmp_path / "h.db")
    st = Store(db)
    st.create_account("Wanderer", "", owner="a:Wanderer")
    st.close()
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def run():
        runner, app, url = await start(db, own=True)
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                ws, m = await come_in(http, url, device_of("phone"), host="the-hosts-own-key", account="Wanderer")
                assert m["account"] == "Wanderer" and [c["name"] for c in m["list"]] == ["Wanderer"]
                await ws.close()
                ws, m = await come_in(http, url, device_of("phone"))            # (no key: the device is theirs here)
                assert m["account"] == "Wanderer" and [c["name"] for c in m["list"]] == ["Wanderer"]
                await ws.close()
                monkeypatch.setattr(game, "central_url", lambda: "http://central.invalid")

                async def down(path, body):
                    return None
                monkeypatch.setattr(game, "central_post", down)
                ws, m = await come_in(http, url, device_of("phone"), ticket="anything")
                assert m["t"] == "characters" and m["account"] == "Wanderer"     # (the central server away)
                await ws.close()
                ws, m = await come_in(http, url, device_of("laptop"), ticket="anything")
                assert m["t"] == "characters" and m["account"] == ""              # (another device: its own)
                await ws.close()
        finally:
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


def test_a_game_on_the_network_answers_who_is_there(tmp_path, monkeypatch):
    from server import lan
    lan_port = free_port()
    monkeypatch.setenv("DS_LAN_PORT", str(lan_port))

    async def run():
        runner, app, url = await start(str(tmp_path / "s.db"))
        none = await asyncio.get_running_loop().run_in_executor(None, lambda: lan.find(0.5, lan_port, ("127.0.0.1",)))
        assert not none                                                 # (a server of its own never answers)
        await runner.cleanup()
        runner, app, url = await start(str(tmp_path / "a.db"), own=True)
        none = await asyncio.get_running_loop().run_in_executor(None, lambda: lan.find(0.5, lan_port, ("127.0.0.1",)))
        assert not none                                                 # (nor an app's, till it's opened)
        app[GAME].store.set_setting("lan_open", "1")
        await app[GAME].network_changed()
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


def test_the_host_can_close_the_game_to_the_network(tmp_path, monkeypatch):
    """Closed to the network: only this machine may join, and the game doesn't answer the network's "who's there?"."""
    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"), own=True)
        game = app[GAME]
        game.store.set_setting("lan_open", "1")
        try:
            async with aiohttp.ClientSession() as http:
                ws, m = await login(http, url, "Hostess", "secret1")
                assert m["t"] == "welcome" and m["host"] and m["lan"]       # (here on this machine: the host)
                await ws.send_json({"t": "lan", "open": False})
                for _ in range(20):
                    await asyncio.sleep(0.05)
                    if not game.lan_open:
                        break
                assert not game.lan_open and game.store.setting("lan_open") == "0"
                assert not game.is_local("192.168.1.20") and game.is_local("127.0.0.1")
                ws2, m2 = await login(http, url, "Neighbour", "secret2")    # (still this machine: let in)
                assert m2["t"] == "welcome"
                await ws2.send_json({"t": "server_name", "name": "Kris's World"})
                await asyncio.sleep(0.3)
                assert game.server_name() == "Kris's World"                 # (the host names the game)
                await ws.close()
                await ws2.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_a_public_server_limits_sign_ups_behind_its_proxy(tmp_path, monkeypatch):
    """Behind Caddy (DS_TRUST_PROXY=1) each player's own address counts: two new characters a day from one, names
    kept back; and from the internet, a Hallisium account (a ticket) or nothing."""
    monkeypatch.setenv("DS_TRUST_PROXY", "1")
    monkeypatch.setenv("DS_REGISTER_PER_DAY", "2")

    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"), own=True)
        game = app[GAME]
        game.store.set_setting("lan_open", "1")
        monkeypatch.setattr(game, "central_url", lambda: "http://central.invalid")

        async def verified(path, body):
            return {"ok": True, "name": body["ticket"]}               # (this test's tickets: the account's name)
        monkeypatch.setattr(game, "central_post", verified)
        try:
            async with aiohttp.ClientSession() as http:
                async def reg(name, addr, account):
                    # (the proxy puts the player's own address last: what's before it is anyone's to write)
                    ws, m = await login(http, url, name, headers={"X-Forwarded-For": "127.0.0.1, " + addr},
                                        auth_with={"ticket": account} if account else None)
                    await ws.close()
                    return m
                m = await reg("Lone", "1.1.1.1", "")
                assert m["t"] == "login_fail" and "Sign in" in m["reason"]                 # (no account)
                assert (await reg("Admin", "1.1.1.1", "Acct"))["t"] == "login_fail"         # (kept back)
                assert (await reg("Firsty", "1.1.1.1", "Acct"))["t"] == "welcome"
                assert (await reg("Secondy", "1.1.1.1", "Acct"))["t"] == "welcome"
                m = await reg("Thirdy", "1.1.1.1", "Other")
                assert m["t"] == "login_fail" and "today" in m["reason"]                   # (two a day from there)
                assert (await reg("Elsewhere", "2.2.2.2", "Other"))["t"] == "welcome"       # (another player)
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_one_address_may_hold_only_so_many_connections(tmp_path, monkeypatch):
    """DS_CONNECTIONS_PER_ADDRESS: past it an address is turned away (429) until one of its own closes; another
    address, and this machine's own, aren't held back."""
    monkeypatch.setenv("DS_TRUST_PROXY", "1")
    monkeypatch.setenv("DS_CONNECTIONS_PER_ADDRESS", "2")

    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"))
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                def at(addr):
                    return http.ws_connect(url, headers={"X-Forwarded-For": addr})
                a, b = await at("1.1.1.1"), await at("1.1.1.1")
                with pytest.raises(aiohttp.WSServerHandshakeError) as e:
                    await at("1.1.1.1")
                assert e.value.status == 429
                other = await at("2.2.2.2")                         # (someone else: let in)
                mine = [await http.ws_connect(url) for _ in range(3)]   # (this machine's own: no limit)
                await a.close()
                for _ in range(50):                                 # (the server notices the close)
                    if game.conns.get("1.1.1.1") == 1:
                        break
                    await asyncio.sleep(0.05)
                c = await at("1.1.1.1")                             # (one closed: room again)
                for ws in (b, c, other, *mine):
                    await ws.close()
                for _ in range(50):
                    if not game.conns:
                        break
                    await asyncio.sleep(0.05)
                assert game.conns == {} and game.turned_away == set()   # (forgotten once all are gone)
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_an_admin_can_ban_kick_and_mute(tmp_path, monkeypatch):
    """A ban is on the character and whose it is: not a new character away."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"), admins="Boss")
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                boss, _ = await login(http, url, "Bossy", auth_with={"host": "the-hosts-own-key", "account": "Boss"})
                pest, _ = await login(http, url, "Pest")
                await boss.send_json({"t": "chat", "text": "/mute Pest 5"})
                await asyncio.sleep(0.3)
                assert game.world.sessions["Pest"].muted_until > 0
                await boss.send_json({"t": "chat", "text": "/ban Pest spamming"})
                await asyncio.sleep(0.5)
                assert game.banned("Pest") == "spamming"
                assert game.ban_words("Out", "spamming") == "Out: spamming" and game.ban_words("Out", "banned") == "Out."
                _, why = await come_in(http, url, device_of("Pest"))
                assert why["t"] == "login_fail" and why["reason"] == "You're banned from this server: spamming"
                again, m = await login(http, url, "Pest", mode="login")
                assert m["t"] == "login_fail" and "banned" in m["reason"]
                fresh, m = await login(http, url, "Pest Two", device=device_of("Pest"))
                assert m["t"] == "login_fail" and "banned" in m["reason"]      # (the same device: still them)
                await boss.send_json({"t": "chat", "text": "/unban Pest"})
                await asyncio.sleep(0.3)
                assert not game.banned("Pest") and not game.banned_owner(game.store.owner("Pest"))
                for ws in (boss, pest, again, fresh):
                    await ws.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_open_pvp_is_the_servers_setting_and_an_admin_turns_it(tmp_path, monkeypatch):
    """DS_PVP=1 opens it; an admin's /pvp off closes it, and that's kept with the world (over DS_PVP)."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")
    monkeypatch.setenv("DS_PVP", "1")

    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"), admins="Boss")
        game = app[GAME]
        try:
            assert game.world.open_pvp
            async with aiohttp.ClientSession() as http:
                boss, _ = await login(http, url, "Bossy", auth_with={"host": "the-hosts-own-key", "account": "Boss"})
                await boss.send_json({"t": "chat", "text": "/pvp off"})
                await asyncio.sleep(0.3)
                assert not game.world.open_pvp and not game.pvp_open()
                await boss.send_json({"t": "chat", "text": "/pvp on"})
                await asyncio.sleep(0.3)
                assert game.world.open_pvp and game.store.setting("pvp") == "1"
                await boss.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())


async def chats(ws, seconds=0.6):
    """The chat lines that come in a moment."""
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


def test_moderation_holds_and_chat_isnt_a_flood(tmp_path, monkeypatch):
    """A muted player can't whisper either; nobody floods the chat; /ban takes a name with spaces, /unban undoes it."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def go():
        runner, app, url = await start(str(tmp_path / "m.db"), admins="Boss")
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                boss, _ = await login(http, url, "Boss", auth_with={"host": "the-hosts-own-key", "account": "Boss"})
                pest, _ = await login(http, url, "Old Pest")
                await boss.send_json({"t": "chat", "text": "/mute Old Pest 5"})
                await asyncio.sleep(0.3)
                assert game.world.sessions["Old Pest"].muted_until > 0          # (a name with a space)
                await pest.send_json({"t": "chat", "text": "/w Boss hello"})
                said = await chats(pest)
                assert any("muted" in m["text"] for m in said)
                game.world.sessions["Old Pest"].muted_until = 0
                for k in range(10):
                    await pest.send_json({"t": "chat", "text": "spam %d" % k})
                heard = await chats(boss, 1.0)
                assert len([m for m in heard if m.get("from") == "Old Pest"]) <= 6        # (no more than six at once)
                await boss.send_json({"t": "chat", "text": "/ban Old Pest being a pest"})
                await asyncio.sleep(0.5)
                assert game.banned("Old Pest") == "being a pest"
                await boss.send_json({"t": "chat", "text": "/unban Old Pest"})
                await asyncio.sleep(0.3)
                await boss.send_json({"t": "chat", "text": "/bans"})
                assert any("nobody" in m["text"] for m in await chats(boss))
                await boss.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_only_the_games_own_page_may_join(tmp_path):
    async def go():
        runner, app, url = await start(str(tmp_path / "o.db"))
        try:
            async with aiohttp.ClientSession() as http:
                with pytest.raises(aiohttp.WSServerHandshakeError):
                    await http.ws_connect(url, headers={"Origin": "https://evil.example"})
                host = url.split("//")[1].split("/")[0]
                ws = await http.ws_connect(url, headers={"Origin": "http://" + host})     # (its own page)
                await ws.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_an_older_world_save_is_put_on_utc(tmp_path):
    from ashen.lb import clock_seconds, local_offset
    db = str(tmp_path / "u.db")
    due = clock_seconds() + local_offset() + 3600                      # (an hour off, in local time as it was kept)
    st = Store(db)
    st.save_world({"queue": ["ADD\tOld_Thing\tMapItem\t1\t1,1,0\t100,100\t3600\t%d" % due],
                   "farms": [["3,3,0", 5, 14, "Potato", "Someone", float(due)]]})
    st.close()

    async def go():
        runner, app, url = await start(db)
        try:
            w = app[GAME].world
            entry = next(q for q in w.action_queue if "Old_Thing" in q)
            assert abs(float(entry.split("\t")[-1]) - (clock_seconds() + 3600)) < 60
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_a_closed_server_makes_no_character_for_a_ticket(tmp_path, monkeypatch):
    async def go():
        runner, app, url = await start(str(tmp_path / "c.db"))
        game = app[GAME]
        game.registration = "closed"
        monkeypatch.setattr(game, "central_url", lambda: "http://central.invalid")

        async def verified(path, body):
            return {"ok": True, "name": "Stranger"}
        monkeypatch.setattr(game, "central_post", verified)
        try:
            async with aiohttp.ClientSession() as http:
                ws, m = await come_in(http, url, device_of("Stranger"), ticket="anything")
                assert m["t"] == "characters" and m["account"] == "Stranger" and not m["make"]
                await ws.send_json({"t": "create", "name": "Stranger"})
                m = await replies(ws, ("welcome", "login_fail"))
                assert m["t"] == "login_fail" and game.store.account("Stranger") is None
                await ws.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())



def test_a_servers_name_is_what_its_given_and_never_a_containers_number(monkeypatch):
    from types import SimpleNamespace
    from server.game import GameServer
    saved = {}
    remote = []
    me = SimpleNamespace(store=SimpleNamespace(setting=lambda k, d="": saved.get(k, d)), default_name="",
                         remote=lambda: bool(remote))
    name = lambda: GameServer.server_name(me)                     # noqa: E731
    monkeypatch.delenv("DS_NAME", raising=False)
    assert name().startswith("Shards of Ashen on ")               # (at home: this machine's)
    remote.append(True)
    assert name() == "A Shards of Ashen server"                   # (listed: the same whichever container it's in)
    monkeypatch.setenv("DS_NAME", "The Ashen Inn")
    assert name() == "The Ashen Inn"                              # (the Unraid template's Server name)
    saved["name"] = "Kris's World"
    assert name() == "Kris's World"                               # (an admin's, in Options)


def test_the_ticket_says_whether_a_player_has_the_full_game(tmp_path, monkeypatch):
    """The central server's word, with the ticket (dsengine/demo.py): no demo till it says there is one; then an account
    without the full game plays the Isle, one with it everything, and a friend of one who has it while they're both
    in the game (the Friend Pass); a time pass run out is asked about again."""
    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"))
        game = app[GAME]
        monkeypatch.setattr(game, "central_url", lambda: "http://central.invalid")
        owns, demo, until, asked = {"Buyer": True, "Trier": False}, [False], [0], []

        async def central(path, body, packed=False):
            if path == "/api/verify":
                n = body["ticket"]
                return {"ok": True, "name": n, "grant": "g-" + n, "demo": demo[0], "pass_until": until[0],
                        "full": owns[n] or not demo[0] or until[0] > time.time() - 60,
                        "friends": {"Trier": ["Buyer"], "Buyer": ["Trier"]}[n]}
            if path == "/api/game/owns":
                asked.append(body["grant"])
                return {"ok": True, "name": body["grant"][2:], "full": owns[body["grant"][2:]], "pass_until": 0}
            return {"ok": True, "same": True}
        monkeypatch.setattr(game, "central_post", central)
        try:
            async with aiohttp.ClientSession() as http:
                async def come(name, mode="login"):
                    ws, m = await login(http, url, name, mode=mode, auth_with={"ticket": name})
                    assert m["t"] == "welcome"
                    return ws, game.world.sessions[name]
                ws, s = await come("Trier", "register")
                assert s.full and not s.demo()                              # (no demo yet: all of it)
                await ws.close()
                demo[0] = True
                ws, s = await come("Trier")
                assert not s.full and s.demo() and game.store.setting("full:trier") == ""
                await ws.close()
                ws, s = await come("Trier")
                game.friend_passes()
                assert not s.friend_pass                                    # (no friend of theirs who owns it here)
                wb, b = await come("Buyer", "register")
                assert b.full and not b.demo()
                game.friend_passes()
                assert s.friend_pass and not s.demo()                       # (a friend's here: the Friend Pass)
                await wb.close()
                for _ in range(50):
                    if not b.connected:
                        break
                    await asyncio.sleep(0.05)
                game.friend_passes()
                assert not s.friend_pass and s.demo()                       # (gone: on the Isle, the demo at once)
                await ws.close()
                until[0] = int(time.time()) - 1                             # (a time pass, just run out)
                ws, s = await come("Trier")
                assert s.full and s.pass_until
                game.passes_ran_out()
                for _ in range(50):
                    if asked:
                        break
                    await asyncio.sleep(0.05)
                await asyncio.sleep(0.1)
                assert asked == ["g-Trier"] and not s.full and s.demo() and not s.pass_until
                await ws.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())


def test_an_apps_own_game_is_the_full_game_for_its_guests_while_its_host_owns_it(tmp_path, monkeypatch):
    """An app's own game (no central server needed): its app says whether there's a demo and whether the device
    has the full game; a guest has the Friend Pass while someone who owns it is in a game whose host owns it."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def go():
        runner, app, url = await start(str(tmp_path / "o.db"), own=True)
        game = app[GAME]
        try:
            async with aiohttp.ClientSession() as http:
                def host(full):
                    return {"host": "the-hosts-own-key", "account": "", "demo": True, "full": full}
                wh, m = await login(http, url, "Hosty", auth_with=host(False))
                h = game.world.sessions["Hosty"]
                assert m["t"] == "welcome" and h.demo()                     # (not bought on the device: the demo)
                wg, m = await login(http, url, "Guesty")
                g = game.world.sessions["Guesty"]
                game.friend_passes()
                assert g.demo() and not g.friend_pass                       # (nobody here owns it)
                await wh.close()
                wh, m = await login(http, url, "Hosty", mode="login", auth_with=host(True))
                h = game.world.sessions["Hosty"]
                assert h.full and not h.demo()                              # (bought: the full game)
                game.friend_passes()
                assert g.friend_pass and not g.demo()                       # (the host owns it, and is here)
                game.clients[g].addr = "relay:203.0.113.9"
                game.friend_passes()
                assert not g.friend_pass                    # (through the relay: the device's word isn't enough)
                game.clients[g].addr = "127.0.0.1"
                game.friend_passes()
                assert g.friend_pass
                await wh.close()
                for _ in range(50):
                    if not h.connected:
                        break
                    await asyncio.sleep(0.05)
                game.friend_passes()
                assert not g.friend_pass and g.demo()                       # (gone: the demo again, on the Isle)
                await wg.close()
        finally:
            await runner.cleanup()
    asyncio.run(go())
