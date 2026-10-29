"""Finding a game on the same network (the Android app's "Games on this network"): the server answers a UDP
broadcast. Anything on the network sends PROBE to UDP port DS_LAN_PORT (8485) of 255.255.255.255; every server there
answers, to whoever asked, with what it is:

  {"game": "shardsofashen", "name": "Kris's world", "port": 8484, "online": 2, "max": 5, "version": "1.0.116"}

DS_LAN=0 turns it off. (A server in Docker is only found with host networking: broadcasts don't cross Docker's own
network. Anyone can still join it by its address.)"""
import asyncio
import json
import logging
import os
import socket
import time

log = logging.getLogger("ashen.lan")
PROBE = b"SHARDSOFASHEN?"


class Responder(asyncio.DatagramProtocol):
    def __init__(self, about):
        self.about = about                       # () -> the answer, as a dict
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if data.strip() != PROBE:
            return
        try:
            self.transport.sendto(json.dumps(self.about()).encode("utf-8"), addr)
        except OSError:
            pass                                 # (whoever asked has gone)


async def start(about, port=None):
    """Answers probes on the LAN port: the transport (close it to stop), or None if it's off or the port's taken."""
    if os.environ.get("DS_LAN", "1").strip() in ("0", "no", "off", "false"):
        return None
    port = int(os.environ.get("DS_LAN_PORT", "8485")) if port is None else port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError as e:
        sock.close()
        log.warning("Not answering on the network (UDP %d): %s", port, e)
        return None
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(lambda: Responder(about), sock=sock)
    log.info("Answering games-on-this-network on UDP %d", port)
    return transport


def find(seconds=1.5, port=8485, to=("255.255.255.255",)):
    """The games answering on the network: [(address, answer)], each once (for tools and tests; the app has its own)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    found = {}
    try:
        for host in to:
            try:
                sock.sendto(PROBE, (host, port))
            except OSError:
                pass
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                answer = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            if answer.get("game") == "shardsofashen":
                found[(addr[0], answer.get("port"))] = (addr[0], answer)
    finally:
        sock.close()
    return list(found.values())
