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
