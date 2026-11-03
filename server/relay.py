"""Hosting for friends: the game connects out to the central server (no port opened on the host's router, any network,
a phone's too) and the central server passes its friends' visits through that one connection. A friend's browser
opens <central>/play/<this game's id>/: each page or picture asked for there comes here as a "get" and goes back as a
"res"; a friend's game connection is an "open", its messages "m" both ways, and a "close". Here, each is passed to
this same server on 127.0.0.1, its game connection marked as relayed (auth.RELAY_KEY), so it's never taken for this
machine: game.py lets only the host and the host's friends in by that way.

The key it connects with is the host's (from the ticket the host came in with): the central server knows the game by
it, and lists it for the host's friends while it's connected."""
import asyncio
import base64
import json
import logging
from urllib.parse import quote, urlencode

from . import auth

log = logging.getLogger("ashen.relay")

TUNNEL_MAX = 64 * 1024 * 1024        # (the biggest message either way: a picture, base64)
RETRY = (2, 5, 10, 30, 60)           # (seconds before connecting again, after each failure in a row)


class Relay:
    def __init__(self, game, port):
        self.game, self.port = game, port
        self.up = False
        self.tunnel = None
        self.conns = {}              # the central server's connection id -> queue of messages for the game
        self.tasks = set()

    def page_version(self):
        """What the central server keeps this game's files by: new pictures or new code are new files."""
        assets = self.game.assets_version()
        return "%s-%s" % (assets, self.game.code_version()) if assets else ""

    def url(self):
        base = self.game.central_url()
        base = "wss://" + base[8:] if base.startswith("https://") else "ws://" + base[7:] if base.startswith("http://") \
            else base
        return base + "/api/relay?" + urlencode({"grant": self.game.host_grant, "key": self.game.server_id(),
                                                 "place": self.game.server_name(),
                                                 "version": self.page_version()})

    async def run(self):
        """Connected to the central server while this game is hosted for friends, the host's key at hand; again after
        a drop (a while later each time it fails in a row)."""
        import aiohttp
        fails = 0
        while True:
            if not (self.game.central_url() and self.game.host_grant):
                await asyncio.sleep(5)
                continue
            try:
                async with aiohttp.ClientSession() as http:
                    # (compressed: everything a game's friends get goes through this, and it's mostly JSON)
                    async with http.ws_connect(self.url(), heartbeat=20, max_msg_size=TUNNEL_MAX, compress=15) as tunnel:
                        self.tunnel, self.up, fails = tunnel, True, 0
                        log.info("Open to friends through the central server")
                        async for msg in tunnel:
                            if msg.type != aiohttp.WSMsgType.TEXT:
                                break
                            try:
                                data = json.loads(msg.data)
                            except ValueError:
                                continue
                            if isinstance(data, dict):
                                self.handle(http, data)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("The central server's relay: %s", e)
            if self.up:
                log.info("Not open to friends just now (the central server's gone): trying again")
            self.up, self.tunnel = False, None
            for q in self.conns.values():
                q.put_nowait(None)
            self.conns.clear()
            await asyncio.sleep(RETRY[min(fails, len(RETRY) - 1)])
            fails += 1

    def stopped(self):
        """Its host has closed it to the internet: whoever came in this way goes too."""
        self.up, self.tunnel = False, None
        for q in self.conns.values():
            q.put_nowait(None)
        self.conns.clear()

    async def send(self, data):
        t = self.tunnel
        if t is not None and not t.closed:
            try:
                await t.send_str(json.dumps(data, separators=(",", ":")))
            except (ConnectionResetError, RuntimeError):
                pass

    def later(self, coro):
        task = asyncio.ensure_future(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def handle(self, http, data):
        t = data.get("t")
        if t == "get":
            self.later(self.fetch(http, data.get("r"), str(data.get("p", ""))))
        elif t == "open":
            cid = data.get("c")
            if cid not in self.conns:
                self.conns[cid] = asyncio.Queue()
                self.later(self.pipe(http, cid, str(data.get("ip", ""))))
        elif t == "m":
            q = self.conns.get(data.get("c"))
            if q is not None:
                q.put_nowait(str(data.get("d", "")))
        elif t == "close":
            q = self.conns.get(data.get("c"))
            if q is not None:
                q.put_nowait(None)

    async def fetch(self, http, rid, path):
        """A page or a picture of this game's, for a friend's browser."""
        path = quote(path.lstrip("/"), safe="/?=&%.-_~:@!$'()*+,;")
        try:
            async with http.get("http://127.0.0.1:%d/%s" % (self.port, path)) as r:
                body = await r.read()
                await self.send({"t": "res", "r": rid, "s": r.status, "ct": r.headers.get("Content-Type", ""),
                                 "cc": r.headers.get("Cache-Control", ""), "b": base64.b64encode(body).decode()})
        except Exception as e:
            log.warning("A friend's page %s: %s", path, e)
            await self.send({"t": "res", "r": rid, "s": 502, "ct": "text/plain", "cc": "", "b": ""})

    async def pipe(self, http, cid, ip):
        """A friend's game connection: to this server as relayed, both ways, till either end closes."""
        q = self.conns[cid]
        try:
            headers = {"X-DS-Relay": auth.RELAY_KEY, "X-DS-Relay-IP": ip[:64]}
            async with http.ws_connect("ws://127.0.0.1:%d/ws" % self.port, headers=headers,
                                       max_msg_size=TUNNEL_MAX) as ws:     # (the game's own: a map is big)
                async def out():
                    async for msg in ws:
                        if msg.type.name != "TEXT":
                            break
                        await self.send({"t": "m", "c": cid, "d": msg.data})
                reader = asyncio.ensure_future(out())
                reader.add_done_callback(lambda _: q.put_nowait(None))     # (the game closed it: done here too)
                try:
                    while True:
                        text = await q.get()
                        if text is None or ws.closed:
                            break
                        await ws.send_str(text)
                finally:
                    reader.cancel()
        except Exception as e:
            log.warning("A friend's connection: %s", e)
        finally:
            self.conns.pop(cid, None)
            await self.send({"t": "close", "c": cid})
