"""The server: who's playing and their characters, the player limit, saving and loading the world."""
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
    """DS_ADMINS names Shards accounts (proved by a ticket, or the host's key), never a new character's name. An old
    character it named before (a password of its own) keeps the Admin button."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")
    db = str(tmp_path / "a.db")
    st = Store(db)
    st.create_account("Olda", auth.hash_password("oldpass1"))
    st.create_account("Devo", "", owner="d:somedevice")
    st.close()

    async def run():
        runner, app, url = await start(db, admins="Kris, ann, Olda, Devo")
        assert app[GAME].store.account("Olda")[2] and not app[GAME].store.account("Devo")[2]
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


def test_an_old_character_is_brought_in_with_its_password(tmp_path, monkeypatch):
    """A character from before accounts (a password of its own): its password once, and it's yours, with no password.
    An admin can give one a password to bring it in with, never one that's someone's already."""
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def run():
        runner, app, url = await start(str(tmp_path / "p.db"), admins="Boss")
        game = app[GAME]
        game.store.create_account("Oldie", auth.hash_password("oldpass1"))
        game.store.set_setting("recover:oldie", "something")
        game.store.create_account("Lost", "")
        try:
            async with aiohttp.ClientSession() as http:
                ws, m = await come_in(http, url, device_of("mine"))
                assert m["t"] == "characters" and m["list"] == [] and m["old"] and m["make"]
                await ws.send_json({"t": "claim", "name": "Oldie", "password": "wrong"})
                m = await replies(ws, ("characters", "login_fail"))
                assert m["t"] == "login_fail" and m["old"]
                await ws.send_json({"t": "claim", "name": "oldie", "password": "oldpass1"})
                m = await replies(ws, ("characters", "login_fail"))
                assert m["t"] == "characters" and [c["name"] for c in m["list"]] == ["Oldie"]
                assert "yours now" in m["text"] and not m["old"]                # (Lost has no password: not waiting)
                assert game.store.account("Oldie")[1] == "" and not game.store.setting("recover:oldie")
                await ws.send_json({"t": "play", "name": "Oldie"})
                assert (await replies(ws, ("welcome", "login_fail")))["t"] == "welcome"
                await ws.close()
                ws, m = await come_in(http, url, device_of("theirs"))
                await ws.send_json({"t": "claim", "name": "Oldie", "password": "oldpass1"})
                assert (await replies(ws, ("characters", "login_fail")))["t"] == "login_fail"     # (it's someone's)
                await ws.close()

                boss, _ = await login(http, url, "Bossy", auth_with={"host": "the-hosts-own-key", "account": "Boss"})
                await boss.send_json({"t": "admin_password", "name": "Oldie", "new": "fresh1"})
                m = await wait_for(boss, "admin_status")
                assert m and "someone's already" in m["text"]
                await boss.send_json({"t": "admin_password", "name": "Lost", "new": "fresh1"})
                m = await wait_for(boss, "admin_status")
                assert m and "Lost's password is set" in m["text"]
                nobody, _ = await login(http, url, "Nobody")                     # (not an admin: ignored)
                await nobody.send_json({"t": "admin_password", "name": "Lost", "new": "hacked"})
                await asyncio.sleep(0.5)
                ws, m = await come_in(http, url, device_of("the lost one"))
                await ws.send_json({"t": "claim", "name": "Lost", "password": "fresh1"})
                m = await replies(ws, ("characters", "login_fail"))
                assert m["t"] == "characters" and m["list"][0]["name"] == "Lost"
                for w in (ws, boss, nobody):
                    await w.close()
        finally:
            await runner.cleanup()
    asyncio.run(run())


def test_a_device_keeps_its_own_characters(tmp_path, monkeypatch):
    """A device's key (no Shards account) has its characters here, at most MOST_CHARACTERS; names are one of a kind on
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
    assert g.devices_welcome("127.0.0.1") and g.devices_welcome("192.168.1.20") and g.devices_welcome("::1")
    assert not g.devices_welcome("8.8.8.8") and not g.devices_welcome("")
    monkeypatch.setenv("DS_PUBLIC", "1")
    assert not g.devices_welcome("192.168.1.20")                                # (a public server: accounts only)


def test_the_host_and_an_account_need_no_network(tmp_path, monkeypatch):
    """The app's own game lets its host in by the key it was started with, as their account, no central server; the
    device that came in by an account (a ticket, or the host's key) is that account's here from then on, so a reload,
    or the central server away, is still them. Characters a ticket made before characters had owners are their
    account's."""
    db = str(tmp_path / "h.db")
    st = Store(db)
    st.create_account("Wanderer", "")
    st.set_setting("central:wanderer", "1")
    st.close()
    monkeypatch.setenv("DS_HOST_KEY", "the-hosts-own-key")

    async def run():
        runner, app, url = await start(db)
        game = app[GAME]
        assert game.store.owner("Wanderer") == "a:Wanderer" and not game.store.setting("central:wanderer")
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


async def claim(http, url, name, password):
    ws, _ = await come_in(http, url, device_of("claimer"))
    await ws.send_json({"t": "claim", "name": name, "password": password})
    m = await replies(ws, ("characters", "login_fail"))
    await ws.close()
    return m


def test_too_many_wrong_passwords_wait(tmp_path):
    async def run():
        runner, app, url = await start(str(tmp_path / "t.db"))
        app[GAME].store.create_account("Guarded", auth.hash_password("right-one"))
        try:
            async with aiohttp.ClientSession() as http:
                reasons = [(await claim(http, url, "Guarded", "wrong")).get("reason", "") for _ in range(6)]
                assert reasons[:5] == ["That name and password don't go together."] * 5
                assert "Too many wrong passwords" in reasons[5]
                m = await claim(http, url, "Guarded", "right-one")
                assert m["t"] == "login_fail" and "Too many" in m["reason"]     # (even the right one, for a while)
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


def test_the_host_can_close_the_game_to_the_network(tmp_path, monkeypatch):
    """Closed to the network: only this machine may join, and the game doesn't answer the network's "who's there?"."""
    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"))
        game = app[GAME]
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
    kept back; and from the internet, a Shards account (a ticket) or nothing."""
    monkeypatch.setenv("DS_TRUST_PROXY", "1")
    monkeypatch.setenv("DS_REGISTER_PER_DAY", "2")

    async def go():
        runner, app, url = await start(str(tmp_path / "t.db"))
        game = app[GAME]
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


def test_only_the_games_own_page_may_join_and_guesses_count_at_once(tmp_path):
    async def go():
        runner, app, url = await start(str(tmp_path / "o.db"))
        try:
            async with aiohttp.ClientSession() as http:
                with pytest.raises(aiohttp.WSServerHandshakeError):
                    await http.ws_connect(url, headers={"Origin": "https://evil.example"})
                host = url.split("//")[1].split("/")[0]
                ws = await http.ws_connect(url, headers={"Origin": "http://" + host})     # (its own page)
                await ws.close()
                app[GAME].store.create_account("Guarded", auth.hash_password("rightpass1"))

                async def guess():
                    return (await claim(http, url, "Guarded", "wrongpass")).get("reason", "")
                said = await asyncio.gather(*[guess() for _ in range(20)])
                assert sum("don't go together" in r for r in said) <= 5     # (twenty at once: only five are tried)
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
