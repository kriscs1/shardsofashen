"""The desktop app's side of the start screen (desktop/app.py): hosting a game here, finding it on the network, the
start screen with the app written into it. (Its window is pywebview's: not opened here.)"""
import json
import os
import socket
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "desktop"))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_the_desktop_app_hosts_finds_and_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("DS_DESKTOP_DATA", str(tmp_path))
    monkeypatch.setenv("DS_DESKTOP_PORT", str(free_port()))
    monkeypatch.setenv("DS_LAN_PORT", str(free_port()))
    import importlib
    import app as desktop
    importlib.reload(desktop)
    b = desktop.Bridge()
    page = desktop.home_page(b)
    assert "window.DSApp" in page and "DS_CENTRAL_DEFAULT" in page and 'src="config.js"' not in page
    b.hostAs("Desk World", "local", "")
    for _ in range(600):
        if json.loads(b.state())["status"] in ("on", "error"):
            break
        time.sleep(0.1)
    st = json.loads(b.state())
    assert st["status"] == "on" and st["name"] == "Desk World" and st["mode"] == "local", st
    try:
        from server import lan
        found = [a for _, a in lan.find(1.5, port=int(os.environ["DS_LAN_PORT"]), to=("127.0.0.1",))]
        assert any(g["name"] == "Desk World" and g.get("id") for g in found)
        assert os.path.exists(os.path.join(str(tmp_path), "ShardsOfAshen", "world.db"))
    finally:
        b.stopHosting()
        for _ in range(300):
            if json.loads(b.state())["status"] == "off":
                break
            time.sleep(0.1)
    assert json.loads(b.state())["status"] == "off"
