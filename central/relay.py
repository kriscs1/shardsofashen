"""Games hosted for friends, passed through here (server/relay.py is the host's end). A host's game connects to
/api/relay with the key its host's ticket brought; while it's connected, its host's friends see it ("hosting") and
open it at /play/<its id>/: the page and its pictures are asked of the host ("get", "res"; what's the same for every
game of a version is kept here, so it's sent through once), and a friend's game connection is passed both ways
("open", "m", "close"). Only the host's friends get in: the host's game checks each one's ticket."""
import asyncio
import base64
import itertools
import json
import logging
import time

from aiohttp import web, WSMsgType

from server import auth

log = logging.getLogger("ashen.central")

TUNNEL_MAX = 64 * 1024 * 1024
ASK_SECONDS = 30                  # (a page or picture the host hasn't sent by then: gone)
CONNS_MOST = 12                   # (friends' connections at once through one game: its 5 players and some to spare)
KEPT_MOST = 400 * 1024 * 1024     # (the pictures kept here, every version's: past this, the oldest go)
KEPT_PATHS = ("assets/", "img/", "js/", "css/")


class Tunnel:
    def __init__(self, ws, account, key, place, version):
        self.ws, self.account, self.key, self.place, self.version = ws, account, key, place, version
        self.conns = {}               # connection id -> the friend's WebSocketResponse
        self.asks = {}                # request id -> future
        self.made = time.time()

    async def send(self, data):
        if not self.ws.closed:
            await self.ws.send_str(json.dumps(data, separators=(",", ":")))


class Relays:
    def __init__(self, store):
        self.store = store
        self.tunnels = {}             # game id -> Tunnel
        self.ids = itertools.count(1)
        self.kept = {}                # (version, path) -> (status, content type, cache control, body)
        self.kept_bytes = 0

    def hosting(self, accounts):
        """{account: {"key", "place"}} for those of accounts hosting a game for friends just now."""
        low = {a.lower(): a for a in accounts}
        return {low[t.account.lower()]: {"key": t.key, "place": t.place}
                for t in self.tunnels.values() if t.account.lower() in low}

    async def stop_hosting(self, account):
        """An account deleted: the games it's hosting for friends close (its key's gone, so they can't come back)."""
        for t in [t for t in self.tunnels.values() if t.account.lower() == account.lower()]:
            await t.ws.close()

    # ----- the host's end
    async def host(self, request):
        q = request.query
        got = self.store.grant_name(q.get("grant", ""))
        key = str(q.get("key", ""))[:64]
        if not got or got[1] != key:
            return web.Response(status=403, text="That key isn't good for this game.")
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=TUNNEL_MAX)
        await ws.prepare(request)
        t = Tunnel(ws, got[0], key, str(q.get("place", ""))[:60], str(q.get("version", ""))[:40])
        old = self.tunnels.get(key)
        self.tunnels[key] = t
        if old is not None:
            await old.ws.close()
        log.info("%s is hosting %s for friends", t.account, t.place or key)
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    break
                try:
                    data = json.loads(msg.data)
                except ValueError:
                    continue
                if isinstance(data, dict):
                    await self.from_host(t, data)
        finally:
            if self.tunnels.get(key) is t:
                del self.tunnels[key]
            for f in t.asks.values():
                if not f.done():
                    f.set_result(None)
            for c in list(t.conns.values()):
                await c.close()
            log.info("%s stopped hosting %s", t.account, t.place or key)
        return ws

    async def from_host(self, t, data):
        kind = data.get("t")
        if kind == "res":
            f = t.asks.pop(data.get("r"), None)
            if f is not None and not f.done():
                f.set_result(data)
        elif kind == "m":
            c = t.conns.get(data.get("c"))
            if c is not None and not c.closed:
                await c.send_str(str(data.get("d", "")))
        elif kind == "close":
            c = t.conns.pop(data.get("c"), None)
            if c is not None:
                await c.close()

    # ----- a friend's end
    async def play(self, request):
        key = request.match_info["key"]
        path = request.match_info.get("path", "")
        t = self.tunnels.get(key)
        if t is None:
            return web.Response(status=404, content_type="text/html", text="<!doctype html><meta charset=utf-8>"
                                "<p style='font:18px serif;padding:2em'>That game isn't open to friends just now.</p>")
        if path == "ws":
            return await self.friend(request, t)
        if request.method != "GET":
            return web.Response(status=405)
        ask = path + ("?" + request.query_string if request.query_string else "")
        kept = self.kept.get((t.version, ask)) if t.version else None
        if kept is None:
            rid = next(self.ids)
            f = asyncio.get_running_loop().create_future()
            t.asks[rid] = f
            await t.send({"t": "get", "r": rid, "p": ask})
            try:
                got = await asyncio.wait_for(f, ASK_SECONDS)
            except asyncio.TimeoutError:
                got = None
            t.asks.pop(rid, None)
            if not got:
                return web.Response(status=504, text="The game didn't answer.")
            kept = (int(got.get("s", 502)), str(got.get("ct", "")), str(got.get("cc", "")),
                    base64.b64decode(got.get("b", "")))
            if t.version and kept[0] == 200 and path.startswith(KEPT_PATHS):
                self.keep((t.version, ask), kept)
        status, ctype, cache, body = kept
        resp = web.Response(status=status, body=body)
        if ctype:
            resp.headers["Content-Type"] = ctype
        if cache:
            resp.headers["Cache-Control"] = cache
        return resp

    def keep(self, k, kept):
        if self.kept_bytes + len(kept[3]) > KEPT_MOST:
            self.kept.clear()
            self.kept_bytes = 0
        self.kept[k] = kept
        self.kept_bytes += len(kept[3])

    async def friend(self, request, t):
        if len(t.conns) >= CONNS_MOST:
            return web.Response(status=503, text="That game is busy.")
        ws = web.WebSocketResponse(heartbeat=5, max_msg_size=65536)
        await ws.prepare(request)
        cid = next(self.ids)
        t.conns[cid] = ws
        await t.send({"t": "open", "c": cid, "ip": auth.client_address(request)})
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await t.send({"t": "m", "c": cid, "d": msg.data})
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            if t.conns.pop(cid, None) is not None:
                await t.send({"t": "close", "c": cid})
        return ws
