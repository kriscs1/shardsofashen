"""The desktop app's side of the start screen (desktop/app.py): hosting a game here, finding it on the network, the
start screen with the app written into it. (Its window is pywebview's: not opened here.)"""
import asyncio
import json
import os
import socket
import sys
import time

import aiohttp

from tests.test_server import replies

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "desktop"))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:     # (Windows keeps some back for UDP alone)
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]


def test_the_desktop_app_hosts_finds_and_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("DS_DESKTOP_DATA", str(tmp_path))
    monkeypatch.setenv("DS_DESKTOP_PORT", str(free_port()))
    monkeypatch.setenv("DS_LAN_PORT", str(free_udp_port()))
    import importlib
    import app as desktop
    importlib.reload(desktop)
    b = desktop.Bridge()
    page = desktop.home_page(b)
    assert "window.DSApp" in page and "DS_CENTRAL_DEFAULT" in page and 'src="config.js"' not in page
    b.hostAs("Desk World", "solo", "", "the-hosts-own-key")
    for _ in range(600):
        if json.loads(b.state())["status"] in ("on", "error"):
            break
        time.sleep(0.1)
    st = json.loads(b.state())
    assert st["status"] == "on" and st["name"] == "Desk World" and st["mode"] == "solo", st
    try:
        from server import lan
        lan_port = int(os.environ["DS_LAN_PORT"])
        assert not lan.find(1.0, port=lan_port, to=("127.0.0.1",))      # (yours alone, as it starts)
        assert os.path.exists(os.path.join(str(tmp_path), "ShardsOfAshen", "solo.db"))
        out = [a for a in desktop.addresses() if not a.startswith("169.254.")]

        def reaches(address):
            try:
                with socket.create_connection((address, st["port"]), 1):
                    return True
            except OSError:
                return False
        assert not out or not reaches(out[0])                           # (not bound to the network yet)

        async def opened():
            # (opened from inside the game: the socket moves, and whoever's playing stays connected)
            url = "ws://127.0.0.1:%d/ws" % st["port"]
            async with aiohttp.ClientSession() as http:
                async with http.ws_connect(url) as ws:
                    await ws.send_json({"t": "auth", "device": "the host's device key", "host": "the-hosts-own-key"})
                    await replies(ws, ("characters",))
                    await ws.send_json({"t": "create", "name": "Hostess"})
                    await replies(ws, ("welcome",))
                    await ws.send_json({"t": "lan", "open": True})
                    await replies(ws, ("lan",))
                    await asyncio.sleep(0.5)
                    found = [a for _, a in await asyncio.to_thread(lan.find, 1.5, lan_port, ("127.0.0.1",))]
                    assert any(g["name"] == "Desk World" and g.get("id") for g in found)
                    if out:
                        assert reaches(out[0])
                    await ws.send_json({"t": "ping", "c": 1})
                    assert (await replies(ws, ("pong",)))["c"] == 1     # (still connected)

                    await ws.send_json({"t": "lan", "open": False})
                    await replies(ws, ("lan",))
                    await asyncio.sleep(0.5)
                    assert not await asyncio.to_thread(lan.find, 1.0, lan_port, ("127.0.0.1",))
                    if out:
                        assert not reaches(out[0])
                    await ws.send_json({"t": "ping", "c": 2})
                    assert (await replies(ws, ("pong",)))["c"] == 2
        asyncio.run(opened())
    finally:
        b.stopHosting()
        for _ in range(300):
            if json.loads(b.state())["status"] == "off":
                break
            time.sleep(0.1)
    assert json.loads(b.state())["status"] == "off"


def pretend_steam(running=True, owns=True, restart=False, ticket=b"\x01\x02\xab"):
    """Steam's library as desktop/owning.py calls it (ctypes), pretended."""
    import ctypes
    import struct
    from types import SimpleNamespace
    kept = []

    def next_callback(pipe, ref):
        if lib.sent:
            return False
        lib.sent = True
        data = struct.pack("<Iii", 77, 1, len(ticket)) + ticket
        buf = ctypes.create_string_buffer(data, len(data))
        kept.append(buf)
        msg = ref._obj
        msg.callback, msg.size = 168, len(data)
        msg.param = ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8))
        return True
    lib = SimpleNamespace(
        sent=False,
        SteamAPI_RestartAppIfNecessary=lambda app: restart,
        SteamAPI_InitFlat=lambda err: 0 if running else 1,
        SteamAPI_SteamApps_v008=lambda: 1234,
        SteamAPI_ISteamApps_BIsSubscribed=lambda apps: owns,
        SteamAPI_SteamUser_v023=lambda: 5678,
        SteamAPI_ManualDispatch_Init=lambda: None,
        SteamAPI_GetHSteamPipe=lambda: 1,
        SteamAPI_ISteamUser_GetAuthTicketForWebApi=lambda user, who: 77 if who.value == b"shardsofashen" else 0,
        SteamAPI_ManualDispatch_RunFrame=lambda pipe: None,
        SteamAPI_ManualDispatch_GetNextCallback=next_callback,
        SteamAPI_ManualDispatch_FreeLastCallback=lambda pipe: None)
    return lib


def test_the_pc_build_is_owned_from_its_store_or_shows_how_to_get_it(tmp_path, monkeypatch):
    """The PC build has no demo (desktop/owning.py): a build of one's own, itch.io's or Epic's is owned (the store's
    download is the purchase); Steam's is owned once Steam says this account owns it, and its Web API ticket goes to the
    central server for the account. The start screen's app knows (fullGame, steamTicket) and never shows an ad."""
    monkeypatch.setenv("DS_DESKTOP_DATA", str(tmp_path))
    import importlib
    import app as desktop
    import owning
    importlib.reload(desktop)

    def made(**store):
        root = tmp_path / ("r%d" % len(list(tmp_path.iterdir())))
        root.mkdir()
        if store:
            (root / "store.json").write_text(json.dumps(store))
        return str(root)
    o = owning.Owning(made())
    assert o.ask() == "yes" and o.state()["full"] is True
    assert owning.Owning(made(store="itch")).state()["full"] is True
    o = owning.Owning(made(store="steam", steam_app="480"))
    assert o.state()["full"] is None                    # (Steam's asked as the app opens)
    assert o.ask() == "no" and o.owned is False and "missing" in o.why
    root = made(store="steam", steam_app="480")
    assert owning.Owning(root, pretend_steam(restart=True)).ask() == "restart"
    o = owning.Owning(root, pretend_steam(running=False))
    assert o.ask() == "no" and "isn't running" in o.why
    o = owning.Owning(root, pretend_steam(owns=False))
    assert o.ask() == "no" and "doesn't own" in o.why
    o = owning.Owning(root, pretend_steam())
    assert o.ask() == "yes" and o.owned is True and o.ticket == ""
    o.ticket_later()
    assert o.ticket == "0102ab"
    b = desktop.Bridge(o)
    st = json.loads(b.state())
    assert st["full"] is True and st["store"] == "steam" and st["steam_ticket"] == "0102ab"
    page = desktop.home_page(b)
    assert "fullGame:" in page and "steamTicket:" in page
    assert 'KIND === "desktop"' in page and "never has an ad" in page


def test_a_games_page_in_the_window_gets_only_the_carried_character(tmp_path, monkeypatch):
    """The bridge answers the start screen; a game's page (a remote server's, a friend's relayed one) may keep and read
    the carried character and go home, and nothing else: not the Steam ticket, the sign-in, hosting or links."""
    from types import SimpleNamespace
    monkeypatch.setenv("DS_DESKTOP_DATA", str(tmp_path))
    import importlib
    import app as desktop
    importlib.reload(desktop)
    monkeypatch.setitem(sys.modules, "ds_host", SimpleNamespace(start=lambda *a: None, stop=lambda: None))
    b = desktop.Bridge()
    shown, loaded, full = [""], [], []
    b._window = SimpleNamespace(get_current_url=lambda: shown[0], load_url=loaded.append,
                                toggle_fullscreen=lambda: full.append(1))
    b.set("token", "the sign-in")
    assert b.get("token") == "the sign-in" and json.loads(b.state())["status"] == "off"   # (the start screen: all of it)
    shown[0] = "https://evil.example/play/"
    assert b.state() == "{}" and b.get("token") == "" and b.find() == []
    b.set("token", "someone else's")
    b.set("central", "https://evil.example")
    b.play("https://evil.example/2")
    b.hostAs("Theirs", "local", "")
    assert b._prefs.get("token") == "the sign-in" and b._prefs.get("central") == "" and not loaded
    assert b._host.status == "off"
    b.fullscreen()                                        # (the game's full-screen button: the whole window)
    assert full == [1] and b._full and "window.pywebview.api.fullscreen()" in desktop.GAME_SHIM
    assert (desktop.GAME_SHIM % "true").endswith("})(true);")       # (the pages' Full screen tick: it's on)
    assert "let full = true;" in desktop.home_page(b)
    b.fullscreen()
    assert full == [1, 1] and not b._full
    b.set("carried", "a character")
    assert b.get("carried") == "a character"                        # (Copy to device, from the game's page)
    assert desktop.Prefs().get("carried") == "a character"          # (kept on disk)
    shown[0] = ""
    b.hostAs("Mine", "local", "")
    for _ in range(50):
        if b._host.status == "on":
            break
        time.sleep(0.05)
    assert b._host.mode == "local" and b._host.status == "on"      # (the mode it was given, not always "solo")
    gone = []
    b._window.destroy = lambda: gone.append(b._host.status)
    shown[0] = "https://evil.example/play/"
    b.quit()
    assert not gone and b._host.status == "on"                      # (a game's page can't close the app)
    shown[0] = ""
    b.quit()                                                        # (the start screen's Exit: saved, stopped, closed)
    assert gone == ["off"]
