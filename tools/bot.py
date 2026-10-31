"""Test players: they come in as a device of their own (making their characters the first time), walk about, click things and chat, and report
what they saw. For trying the server out, and for the load test:

  python tools/bot.py --count 5 --seconds 60 [--url ws://localhost:8484/ws]"""
import argparse
import asyncio
import json
import random
import time

import aiohttp


class Bot:
    def __init__(self, name, url):
        self.name, self.url = name, url
        self.stats = {"messages": 0, "bytes": 0, "snaps": 0, "ents": 0, "maps": 0, "errors": [], "msgs": []}
        self.uid = 0
        self.pos = None
        self.ents = {}

    async def run(self, seconds, actions=True):
        async with aiohttp.ClientSession() as http:
            async with http.ws_connect(self.url) as ws:
                await ws.send_json({"t": "auth", "device": ("bot " + self.name).ljust(16, ".")})
                logged_in = False
                end = time.time() + seconds
                next_act = time.time() + 1
                while time.time() < end:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=0.5)
                    except asyncio.TimeoutError:
                        msg = None
                    if msg is not None:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            break
                        self.stats["bytes"] += len(msg.data)
                        data = json.loads(msg.data)
                        for m in data if isinstance(data, list) else [data]:
                            self.stats["messages"] += 1
                            t = m.get("t")
                            if t == "characters":      # (its own, or made the first time)
                                mine = any(c["name"].lower() == self.name.lower() for c in m["list"])
                                await ws.send_json({"t": "play" if mine else "create", "name": self.name})
                            elif t == "login_fail":
                                self.stats["errors"].append(m["reason"])
                                return self.stats
                            elif t == "welcome":
                                logged_in = True
                                self.uid = m["uid"]
                            elif t == "snap":
                                self.stats["snaps"] += 1
                                self.pos = m["me"]
                                for e in m["add"]:
                                    self.ents[e["u"]] = e
                                for c in m["chg"]:
                                    self.ents.setdefault(c["u"], {}).update(c)
                                for u in m["del"]:
                                    self.ents.pop(u, None)
                                self.stats["ents"] = len(self.ents)
                            elif t == "mapdata":
                                self.stats["maps"] += 1
                            elif t == "msg":
                                self.stats["msgs"].append(m["text"])
                    if logged_in and actions and time.time() >= next_act and self.pos:
                        next_act = time.time() + random.uniform(0.5, 2.0)
                        await self.act(ws)
                await ws.send_json({"t": "quit"})
        return self.stats

    async def act(self, ws):
        r = random.random()
        if r < 0.4:
            await ws.send_json({"t": "move", "dir": random.choice((1, 2, 4, 8, 3, 6, 12, 9, 0))})
        elif r < 0.7:
            x = self.pos["x"] + random.uniform(-200, 200)
            y = self.pos["y"] + random.uniform(-200, 200)
            await ws.send_json({"t": "move", "dir": 0})
            await ws.send_json({"t": "verb", "verb": "Walk here", "x": x, "y": y})
        elif r < 0.9 and self.ents:
            e = random.choice(list(self.ents.values()))
            if "x" in e:
                verb = {3: "Pickup", 5: "Attack" if e.get("f") else "Talk to"}.get(e.get("k"), "Examine")
                await ws.send_json({"t": "verb", "verb": verb, "target": {"k": "ent", "uid": e["u"]}, "x": e["x"],
                                    "y": e["y"]})
        else:
            await ws.send_json({"t": "chat", "text": "Hello from %s" % self.name})
            await ws.send_json({"t": "close"})


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="ws://localhost:8484/ws")
    p.add_argument("--count", type=int, default=2)
    p.add_argument("--seconds", type=float, default=20)
    p.add_argument("--prefix", default="Bot")
    args = p.parse_args()
    bots = [Bot("%s%d" % (args.prefix, i + 1), args.url) for i in range(args.count)]
    t0 = time.time()
    results = await asyncio.gather(*(b.run(args.seconds) for b in bots), return_exceptions=True)
    secs = time.time() - t0
    for b, r in zip(bots, results):
        if isinstance(r, Exception):
            print("%s: FAILED %r" % (b.name, r))
            continue
        print("%s: %d messages, %.1f KB/s, %d snapshots, %d things in view, %d maps, errors %s" % (
            b.name, r["messages"], r["bytes"] / 1024 / secs, r["snaps"], r["ents"], r["maps"], r["errors"]))
        if r["msgs"]:
            print("   last messages:", r["msgs"][-4:])
    async with aiohttp.ClientSession() as http:
        async with http.get(args.url.replace("ws://", "http://").replace("wss://", "https://").replace("/ws", "/health")) as r:
            print("server:", await r.text())


if __name__ == "__main__":
    asyncio.run(main())
