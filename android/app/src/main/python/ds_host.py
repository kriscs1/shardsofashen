"""The game's server on a phone (HostService starts and stops it): the same server/ as on any other machine, from the
game's folder unpacked on the phone, run in a thread of its own so the app goes on while it does."""
import asyncio
import logging
import os
import sys
import threading

_run = {}                                        # loop, runner, thread: while it's running


def start(root, db, name, port, build, solo=False, mode="local", central="", host_key=""):
    """Starts the server on every network the phone is on (port), its world kept in db: back once it's taking players.
    solo: a game of your own (this phone only: on 127.0.0.1, not answering the network, closed to it). mode: local
    (answered on this network) or remote (announced to the central server, listed for everyone). central: the central
    server (accounts: a player comes in by its ticket). host_key: the start screen's own key, that lets it in as the
    host (as its Shards account, or this device) with no ticket: playing alone needs no network."""
    if _run:
        return
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ["DS_NAME"] = name
    os.environ["DS_LAN"] = "0" if solo else "1"                 # (alone: nobody on the network is told of it)
    os.environ["DS_LAN_OPEN"] = "0" if solo else "1"
    os.environ["DS_CENTRAL"] = central or ""
    os.environ["DS_HOST_KEY"] = host_key or ""
    os.environ["DS_PUBLIC"] = "1" if mode == "remote" and not solo else "0"
    os.environ["DS_BUILD"] = str(build)           # (the app's build number: the version on the login screen)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)   # (not a line for every picture fetched)
    from aiohttp import web
    from server.app import make_app

    ready, failed = threading.Event(), []

    def serve():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            app = make_app(root, db, 5, "open", "", name=name, port=port)
            runner = web.AppRunner(app)
            loop.run_until_complete(runner.setup())
            loop.run_until_complete(web.TCPSite(runner, "127.0.0.1" if solo else "0.0.0.0", port).start())
        except BaseException as e:
            failed.append(e)
            ready.set()
            return
        _run.update(loop=loop, runner=runner)
        ready.set()
        loop.run_forever()
        loop.run_until_complete(runner.cleanup())   # (everyone saved, the world too)
        loop.close()

    thread = threading.Thread(target=serve, name="shardsofashen", daemon=True)
    _run["thread"] = thread
    thread.start()
    ready.wait(120)
    if failed:
        _run.clear()
        raise failed[0]


def stop():
    """Stops it, once the world's saved."""
    loop = _run.get("loop")
    if loop is None:
        return
    loop.call_soon_threadsafe(loop.stop)
    _run["thread"].join(60)
    _run.clear()


def running():
    return "loop" in _run
