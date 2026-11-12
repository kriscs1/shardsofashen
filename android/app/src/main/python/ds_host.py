"""The game's server on a phone (HostService starts and stops it): the same server/ as on any other machine, from the
game's folder unpacked on the phone, run in a thread of its own so the app goes on while it does."""
import asyncio
import logging
import os
import sys
import threading

_run = {}                                        # loop, runner, thread: while it's running


def start(root, db, name, port, build, central="", host_key=""):
    """Starts the single-player game, its world kept in db: back once it's taking players. It's this machine's alone (on
    127.0.0.1, not answering the network) till its host opens it, in Options: to the network (make_app's network_changed:
    bind, below), the internet (through the central server, relay.py), or both. central: the central server (accounts: a
    player comes in by its ticket). host_key: the start screen's own key, that lets it in as the host (as its Shards
    account, or this device) with no ticket: playing alone needs no network."""
    if _run:
        return
    older = os.path.join(os.path.dirname(db), "world.db")   # (hosting was a world of its own: it's the one world if alone)
    if not os.path.exists(db) and os.path.exists(older):
        os.replace(older, db)
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ["DS_NAME"] = name
    os.environ["DS_CENTRAL"] = central or ""
    os.environ["DS_HOST_KEY"] = host_key or ""
    os.environ["DS_BUILD"] = str(build)           # (the app's build number: the version on the login screen)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)   # (not a line for every picture fetched)
    from aiohttp import web
    from server.app import make_app, settle, GAME

    ready, failed = threading.Event(), []

    def serve():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            app = make_app(root, db, 5, "open", "", name=name, port=port, own=True)
            settle()
            runner = web.AppRunner(app)
            loop.run_until_complete(runner.setup())
            site = [web.TCPSite(runner, "127.0.0.1", port)]
            loop.run_until_complete(site[0].start())

            async def bind(everywhere):
                # (only the listening socket changes: whoever's playing stays connected)
                await site[0].stop()
                try:
                    site[0] = web.TCPSite(runner, "0.0.0.0" if everywhere else "127.0.0.1", port)
                    await site[0].start()
                except OSError:
                    site[0] = web.TCPSite(runner, "127.0.0.1", port)
                    await site[0].start()
                    raise
            app[GAME].bind_network = bind
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
