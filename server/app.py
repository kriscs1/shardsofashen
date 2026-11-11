"""The web server: the game page and its files (web/), the pictures, sounds and data the browser needs (web/assets,
made by tools/export_web_assets.py), and the game's WebSocket (/ws). It answers "who's there?" on the network
(lan.py), so the Android app finds it. The app runs this same server itself when a phone hosts a game."""
import asyncio
import logging
import os
import signal
import socket

from aiohttp import web

from .game import GameServer, UNNAMED
from .progress import Reporter
from .relay import Relay
from . import lan

log = logging.getLogger("ashen.server")
GAME = web.AppKey("game", GameServer)
TICK = web.AppKey("tick", asyncio.Task)
ANNOUNCE = web.AppKey("announce", object)
PROGRESS = web.AppKey("progress", object)


def make_app(root, db_path, max_players=5, registration="open", invite_code="", admins="", name="", port=8484, own=False):
    game = GameServer(root, db_path, max_players, registration, invite_code, admins=admins)
    game.port, game.own = port, own
    game.bind_network, game.lan_answer, game.relay_task = None, None, None
    if own:                                             # (each time it starts it's yours alone, till you open it)
        game.store.set_setting("lan_open", "0")
        game.store.set_setting("internet_open", "0")
    web_dir = os.path.join(root, "web")
    assets = os.path.join(web_dir, "assets")
    app = web.Application()
    app[GAME] = game
    game.default_name = name                            # (what the host called it: the Android or desktop app)

    async def index(request):
        # (a remote server: only a ticket from the central server, or what its page was given for one: no other way in,
        # this machine and its network no different)
        if game.remote():
            if "ticket" in request.query or game.joined_ok(request.query.get("joined", "")):
                return web.FileResponse(os.path.join(web_dir, "index.html"), headers={"Cache-Control": "no-cache"})
            return web.Response(status=404)
        # (nothing here but for who's come through a client or the central server's start screen, a ticket or what's left
        # of one; this machine; and an app's own game to those on its network, at the address its host gives them)
        if not ({"ticket", "joined", "app"} & set(request.query) or game.is_local(game.client_addr(request))
                or (game.own and game.lan_open)):
            return web.Response(status=404)
        return web.FileResponse(os.path.join(web_dir, "index.html"), headers={"Cache-Control": "no-cache"})

    async def manifest(request):
        return web.FileResponse(os.path.join(web_dir, "manifest.webmanifest"),
                                headers={"Content-Type": "application/manifest+json", "Cache-Control": "no-cache"})

    async def info(request):
        # (a start screen asking who this is before it joins by address: its id for the ticket, its name; a remote server
        # is never joined by address, so it says only that)
        if game.remote():
            return web.json_response({"game": "shardsofashen", "remote": True}, headers={"Access-Control-Allow-Origin": "*"})
        return web.json_response({"game": "shardsofashen", "id": game.server_id(), "name": game.server_name(),
                                  "online": len(game.world.sessions), "max": game.max_players,
                                  "central": bool(game.central_url())},
                                 headers={"Access-Control-Allow-Origin": "*"})

    async def health(request):
        return web.json_response({"ok": True, "online": len(game.world.sessions), "tick_ms": round(game.tick_ms, 2),
                                  **game.version})

    @web.middleware
    async def caching(request, handler):
        resp = await handler(request)
        if request.path.startswith("/assets/") and request.query.get("v"):
            resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")   # (a new version: new address)
        elif request.path.startswith(("/assets/", "/img/")):
            resp.headers.setdefault("Cache-Control", "public, max-age=3600")
        elif request.path.startswith(("/js/", "/css/")):
            resp.headers.setdefault("Cache-Control", "no-cache")
        return resp

    app.middlewares.append(caching)
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get("/api/info", info)
    app.router.add_get("/manifest.webmanifest", manifest)
    app.router.add_get("/ws", game.handle_ws)
    if os.path.isdir(assets):
        app.router.add_static("/assets/", assets)
    else:
        log.warning("web/assets is missing: run tools/export_web_assets.py")
    app.router.add_static("/js/", os.path.join(web_dir, "js"))
    app.router.add_static("/css/", os.path.join(web_dir, "css"))
    app.router.add_static("/img/", os.path.join(web_dir, "img"))

    def about():
        # (the answer to "who's there?" on the network: nothing while it's closed to the network)
        if not game.lan_open:
            return None
        return {"game": "shardsofashen", "id": game.server_id(), "name": game.store.setting("name", "") or name or
                "Shards of Ashen on " + socket.gethostname(), "port": port,
                "online": len(game.world.sessions), "max": game.max_players, "version": game.version["version"]}

    async def announcing():
        while True:                                     # (remote: the central server lists it while it's heard)
            await game.announce()
            await game.keep_friends()                   # (and everyone in by an account: playing here, their friends)
            await asyncio.sleep(60)

    async def network_changed():
        try:
            if game.bind_network:
                await game.bind_network(game.lan_open)
        except OSError as e:
            log.warning("Couldn't open the game to the network: %s", e)
            game.store.set_setting("lan_open", "0")
            game.broadcast({"t": "lan", "open": False})
        if game.lan_open and game.lan_answer is None:
            game.lan_answer = await lan.start(about)
        elif not game.lan_open and game.lan_answer is not None:
            game.lan_answer.close()
            game.lan_answer = None

    async def internet_changed():
        if game.for_friends() and game.relay_task is None:
            game.relay_task = asyncio.create_task(game.relay.run())
            await game.host_friends_now()
        elif not game.for_friends() and game.relay_task is not None:
            game.relay_task.cancel()
            game.relay_task = None
            game.relay.stopped()

    game.network_changed, game.internet_changed = network_changed, internet_changed

    async def start_tick(app):
        app[TICK] = asyncio.create_task(game.run())
        game.lan_answer = None          # (only an app's own game ever answers the network, once it's opened)
        app[ANNOUNCE] = asyncio.create_task(announcing())
        game.relay = Relay(game, port)                  # (hosted for friends: through the central server)
        game.relay_task = asyncio.create_task(game.relay.run()) if game.for_friends() else None
        game.reporter = Reporter(game)                  # (how characters are getting on: the central server's admin page)
        app[PROGRESS] = asyncio.create_task(game.reporter.run())

    async def stop_tick(app):
        app[ANNOUNCE].cancel()
        app[PROGRESS].cancel()
        if game.relay_task is not None:
            game.relay_task.cancel()
        await game.announce(bye=True)
        if game.lan_answer is not None:
            game.lan_answer.close()
        await game.shutdown()
        app[TICK].cancel()

    app.on_startup.append(start_tick)
    app.on_shutdown.append(stop_tick)

    async def close_central(app):
        await game.close_central()

    app.on_cleanup.append(close_central)
    return app


def main():
    import argparse
    p = argparse.ArgumentParser(description="Shards of Ashen multiplayer server")
    root_default = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p.add_argument("--root", default=os.environ.get("DS_ROOT", root_default), help="the game folder (Data, Maps...)")
    p.add_argument("--db", default=os.environ.get("DS_DB", os.path.join(root_default, "server-data", "ashen.db")))
    p.add_argument("--host", default=os.environ.get("DS_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("DS_PORT", "8484")))
    p.add_argument("--max-players", type=int, default=int(os.environ.get("DS_MAX_PLAYERS", "5")))
    p.add_argument("--registration", default=os.environ.get("DS_REGISTRATION", "open"), choices=("open", "closed"))
    p.add_argument("--invite", default=os.environ.get("DS_INVITE_CODE", ""))
    p.add_argument("--admins", default=os.environ.get("DS_ADMINS", ""),
                   help="characters who get the Admin button, comma-separated (as well as tools/admin.py's)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)   # (not a line for every picture and health check)
    app = make_app(args.root, args.db, args.max_players, args.registration, args.invite, args.admins,
                   name=os.environ.get("DS_NAME", ""), port=args.port)
    log.info("Shards of Ashen %s on http://%s:%d (up to %d players)", app[GAME].version["version"], args.host, args.port,
             args.max_players)
    if app[GAME].remote() and app[GAME].server_name() == UNNAMED:
        log.warning("This server has no name: set DS_NAME (Unraid: \"Server name\"), or name it in Options as an admin")
    web.run_app(app, host=args.host, port=args.port, print=None, handle_signals=True)
