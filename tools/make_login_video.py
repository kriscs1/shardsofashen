"""Films the game world for the login screen's background (web/img/login-bg.mp4): the same view as
make_login_background.py (Southport at midday, the fog of war off, the interface left out, the camera's own
character hidden), but moving - the sea and its foam, plants in the wind, townsfolk about their day. The film's end
fades into its start, so it loops without a seam; its first frame is the still (login-bg.jpg, shown while it loads, and to anyone who asks
for less motion). Run it again after changing the maps. Needs playwright and ffmpeg.

  python tools/make_login_video.py [--map 1,3,0] [--x 400 --y 330] [--zoom 0.75] [--seconds 12]"""
import argparse
import asyncio
import base64
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from make_login_background import NAME, PASSWORD, free_port  # noqa: E402
from server import auth  # noqa: E402
from server.store import Store  # noqa: E402

FADE = 2.0          # seconds of the end that fade into the start (the loop's seam)
FPS = 30


async def film(url, frames_dir, zoom, w, h, seconds):
    """The playfield, frame by frame as the browser draws it (Chrome's screencast), with when each was drawn."""
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
            S.me.visible = false;                                    // (the camera, not someone in the picture)
        }""")
        await page.wait_for_timeout(6000)                            # (the pictures load, the camera settles)
        box = await page.evaluate("""() => {
            const W = Math.max(1024, Math.min(1792, Math.round(768 * innerWidth / innerHeight / 2) * 2));
            const k = Math.min(innerWidth / W, innerHeight / 768);
            const ox = (innerWidth - W * k) / 2, oy = (innerHeight - 768 * k) / 2;
            return {x: ox, y: oy + 24 * k, width: (W - 224) * k, height: (672 - 72) * k};
        }""")
        cdp = await page.context.new_cdp_session(page)
        shots = []

        async def on_frame(ev):
            shots.append((ev["metadata"]["timestamp"], ev["data"]))
            await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(on_frame(ev)))
        await cdp.send("Page.startScreencast", {"format": "png", "maxWidth": w, "maxHeight": h, "everyNthFrame": 1})
        await page.wait_for_timeout(int((seconds + FADE + 0.5) * 1000))
        await cdp.send("Page.stopScreencast")
        await browser.close()
    t0 = shots[0][0]
    listing = []
    for n, (t, data) in enumerate(shots):
        name = "f%05d.png" % n
        with open(os.path.join(frames_dir, name), "wb") as f:
            f.write(base64.b64decode(data))
        nxt = shots[n + 1][0] if n + 1 < len(shots) else t + 1.0 / FPS
        listing.append("file '%s'\nduration %.4f" % (name, max(0.001, nxt - t)))
    with open(os.path.join(frames_dir, "frames.txt"), "w") as f:
        f.write("\n".join(listing) + "\nfile '%s'\n" % ("f%05d.png" % (len(shots) - 1)))
    print("%d frames over %.1f s" % (len(shots), shots[-1][0] - t0))
    return box


def encode(frames_dir, box, seconds, out):
    """The frames as a steady film, cut to the playfield; its last FADE seconds fade into its first, so it loops."""
    crop = "crop=%d:%d:%d:%d" % (int(box["width"]) // 2 * 2, int(box["height"]) // 2 * 2, int(box["x"]), int(box["y"]))
    total = seconds + FADE
    graph = ("[0:v]fps=%d,%s,trim=0:%.2f,setpts=PTS-STARTPTS,split[a][b];"
             "[a]trim=%.2f:%.2f,setpts=PTS-STARTPTS[body];"
             "[b]trim=0:%.2f,setpts=PTS-STARTPTS[head];"
             "[body][head]xfade=transition=fade:duration=%.2f:offset=%.2f,format=yuv420p[v]"
             % (FPS, crop, total, FADE, total, FADE, FADE, seconds - FADE))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", os.path.join(frames_dir, "frames.txt"), "-filter_complex", graph, "-map", "[v]",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-tune", "animation",
                    "-movflags", "+faststart", "-an", out], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--map", default="1,3,0")
    p.add_argument("--x", type=int, default=400)
    p.add_argument("--y", type=int, default=330)
    p.add_argument("--zoom", default="0.75")
    p.add_argument("--size", default="1600x900")      # (larger films fewer frames a second: it judders)
    p.add_argument("--seconds", type=float, default=12)
    p.add_argument("--out", default=os.path.join(ROOT, "web", "img", "login-bg.mp4"))
    p.add_argument("--still", default=os.path.join(ROOT, "web", "img", "login-bg.jpg"))
    args = p.parse_args()
    w, h = (int(v) for v in args.size.split("x"))
    tmp = tempfile.mkdtemp(prefix="ds-film-")
    db = os.path.join(tmp, "film.db")
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
        frames = os.path.join(tmp, "frames")
        os.makedirs(frames)
        box = asyncio.run(film("http://127.0.0.1:%d" % port, frames, args.zoom, w, h, args.seconds))
        encode(frames, box, args.seconds, args.out)
        print("%s (%d KB)" % (args.out, os.path.getsize(args.out) // 1024))
        if args.still:                                   # (the film's first frame: the still, while it loads)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.out, "-frames:v", "1", "-q:v", "3",
                            args.still], check=True)
            print("%s (%d KB)" % (args.still, os.path.getsize(args.still) // 1024))
    finally:
        server.terminate()
        server.wait(10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
