"""The web server: the game page and its files (web/), the pictures, sounds and data the browser needs (web/assets,
made by tools/export_web_assets.py), and the game's WebSocket (/ws)."""
import asyncio
import logging
import os
import signal

from aiohttp import web

from .game import GameServer

log = logging.getLogger("dragonsword.server")
GAME = web.AppKey("game", GameServer)
TICK = web.AppKey("tick", asyncio.Task)


def make_app(root, db_path, max_players=5, registration="open", invite_code=""):
    game = GameServer(root, db_path, max_players, registration, invite_code)
    web_dir = os.path.join(root, "web")
    assets = os.path.join(web_dir, "assets")
    app = web.Application()
    app[GAME] = game

    async def index(request):
        return web.FileResponse(os.path.join(web_dir, "index.html"), headers={"Cache-Control": "no-cache"})

    async def health(request):
        return web.json_response({"ok": True, "online": len(game.world.sessions), "tick_ms": round(game.tick_ms, 2)})

    @web.middleware
    async def caching(request, handler):
        resp = await handler(request)
        if request.path.startswith("/assets/"):
            resp.headers.setdefault("Cache-Control", "public, max-age=3600")
        elif request.path.startswith(("/js/", "/css/")):
            resp.headers.setdefault("Cache-Control", "no-cache")
        return resp

    app.middlewares.append(caching)
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get("/ws", game.handle_ws)
    if os.path.isdir(assets):
        app.router.add_static("/assets/", assets)
    else:
        log.warning("web/assets is missing: run tools/export_web_assets.py")
    app.router.add_static("/js/", os.path.join(web_dir, "js"))
    app.router.add_static("/css/", os.path.join(web_dir, "css"))

    async def start_tick(app):
        app[TICK] = asyncio.create_task(game.run())

    async def stop_tick(app):
        await game.shutdown()
        app[TICK].cancel()

    app.on_startup.append(start_tick)
    app.on_shutdown.append(stop_tick)
    return app


def main():
    import argparse
    p = argparse.ArgumentParser(description="Dragon Sword multiplayer server")
    root_default = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p.add_argument("--root", default=os.environ.get("DS_ROOT", root_default), help="the game folder (Data, Maps...)")
    p.add_argument("--db", default=os.environ.get("DS_DB", os.path.join(root_default, "data", "dragonsword.db")))
    p.add_argument("--host", default=os.environ.get("DS_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("DS_PORT", "8080")))
    p.add_argument("--max-players", type=int, default=int(os.environ.get("DS_MAX_PLAYERS", "5")))
    p.add_argument("--registration", default=os.environ.get("DS_REGISTRATION", "open"), choices=("open", "closed"))
    p.add_argument("--invite", default=os.environ.get("DS_INVITE_CODE", ""))
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = make_app(args.root, args.db, args.max_players, args.registration, args.invite)
    log.info("Dragon Sword on http://%s:%d (up to %d players)", args.host, args.port, args.max_players)
    web.run_app(app, host=args.host, port=args.port, print=None, handle_signals=True)
