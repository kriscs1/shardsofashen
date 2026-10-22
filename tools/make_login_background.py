"""Takes a screenshot of the game world for the login screen's background (web/img/login-bg.jpg): a server of its own
with a throwaway database, a character standing on the chosen map at midday, the fog of war off, the interface left
out. Run it again after changing the maps. Needs playwright (pip install playwright; python -m playwright install
chromium) and the web assets (tools/export_web_assets.py).

  python tools/make_login_background.py [--map 1,3,0] [--x 400 --y 330] [--zoom 0.75]"""
import argparse
import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from server import auth  # noqa: E402
from server.store import Store  # noqa: E402

NAME, PASSWORD = "Shutterbug", "picture-time"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def shoot(url, out, zoom, w, h):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h})
        await page.add_init_script("localStorage.setItem('ds.zoom', '%s');"
                                   "localStorage.setItem('ds.view', JSON.stringify({markers: false, smooth: true}));"
                                   % zoom)
        await page.goto(url)
        await page.wait_for_function("document.getElementById('login-online').textContent.includes('online')",
                                     timeout=20000)
        await page.fill("#login-name", NAME)
        await page.fill("#login-password", PASSWORD)
        await page.click("#login-button")
        await page.wait_for_function("document.getElementById('login').hidden && document.getElementById('loading').hidden",
                                     timeout=20000)
        await page.evaluate("""() => {
            const S = window.dsDebug.S;
            S.clock.day = 0.5; S.clock.at = performance.now();       // midday
            S.view = 100000;                                         // everything in view: no fog
            S.players = [];
        }""")
        await page.wait_for_timeout(5000)                            # (the pictures load, the camera settles)
        await page.evaluate("window.dsDebug.S.players = []")
        # the playfield only: the left (W-224) x 672 of the 1024..1792 x 768 layout, scaled to the window
        box = await page.evaluate("""() => {
            const W = Math.max(1024, Math.min(1792, Math.round(768 * innerWidth / innerHeight / 2) * 2));
            const k = Math.min(innerWidth / W, innerHeight / 768);
            const ox = (innerWidth - W * k) / 2, oy = (innerHeight - 768 * k) / 2;
            return {x: ox, y: oy + 24 * k, width: (W - 224) * k, height: (672 - 72) * k};
        }""")
        await page.screenshot(path=out, clip=box, type="jpeg", quality=82)
        await browser.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--map", default="1,3,0")
    p.add_argument("--x", type=int, default=400)
    p.add_argument("--y", type=int, default=330)
    p.add_argument("--zoom", default="0.75")
    p.add_argument("--size", default="2400x1350")
    p.add_argument("--out", default=os.path.join(ROOT, "web", "img", "login-bg.jpg"))
    args = p.parse_args()
    w, h = (int(v) for v in args.size.split("x"))
    tmp = tempfile.mkdtemp(prefix="ds-shot-")
    db = os.path.join(tmp, "shot.db")
    store = Store(db)
    store.create_account(NAME, auth.hash_password(PASSWORD))
    store.save_character(NAME, {"map": args.map, "x": args.x, "y": args.y, "direction": 4})
    store.close()
    port = free_port()
    env = dict(os.environ, DS_DB=db, DS_PORT=str(port), DS_HOST="127.0.0.1")
    server = subprocess.Popen([sys.executable, "-m", "server"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.5)
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        asyncio.run(shoot("http://127.0.0.1:%d" % port, args.out, args.zoom, w, h))
        print("%s (%d KB)" % (args.out, os.path.getsize(args.out) // 1024))
    finally:
        server.terminate()
        server.wait(10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
