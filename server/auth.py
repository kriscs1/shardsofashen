"""Passwords: scrypt (the standard library's), stored as scrypt$n$r$p$salt$hash."""
import base64
import hashlib
import hmac
import ipaddress
import os

N, R, P = 2 ** 14, 8, 1
NAME_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 _-"


def hash_password(password):
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=N, r=R, p=P, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (N, R, P, base64.b64encode(salt).decode(), base64.b64encode(h).decode())


def check_password(password, stored):
    try:
        kind, n, r, p, salt, h = stored.split("$")
        if kind != "scrypt":
            return False
        got = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                             dklen=32)
        return hmac.compare_digest(got, base64.b64decode(h))
    except (ValueError, TypeError):
        return False


CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # (no 0/O, 1/I: easy to copy down)


def recovery_code():
    """A recovery code to write down: four groups of four, e.g. K7QM-2HXA-9WPE-TR3D."""
    picks = [CODE_CHARS[b % len(CODE_CHARS)] for b in os.urandom(16)]
    return "-".join("".join(picks[i:i + 4]) for i in range(0, 16, 4))


def clean_code(entered):
    """A recovery code as typed: any case, spaces or dashes."""
    return "".join(c for c in str(entered).upper() if c in CODE_CHARS)


def clean_name(entered):
    """A character's name as the desktop game allowed them: letters, digits, space, _ and -, at most 20."""
    name = "".join(c for c in str(entered) if c in NAME_CHARS).strip(" ")[:20]
    return "" if name.upper() == "TEMPLATE" else name


RELAY_KEY = os.urandom(16).hex()    # (relay.py's mark on a friend's connection it passes on: this run's own)


def _is_loopback(addr):
    try:
        return ipaddress.ip_address(addr).is_loopback
    except ValueError:
        return addr.lower() == "localhost"


def client_address(request):
    """Who's connecting. A friend's game connection through the central server (relay.py, marked with RELAY_KEY):
    "relay:<their address>", never this machine or its network. Behind a reverse proxy (Caddy on a cloud server, DS_TRUST_PROXY=1): the last address in
    X-Forwarded-For, the one the proxy put there (the ones before it are anyone's to write), and only when the
    connection itself is from the proxy (this machine or a private network: a port published straight to the world
    gets no say). A proxy nobody said was there (no DS_TRUST_PROXY), or one saying it's passing on this machine:
    "proxied:<that address>", never this machine or its network, whatever the connection looks like. Otherwise the
    connection's own address."""
    remote = request.remote or ""
    mark = request.headers.get("X-DS-Relay", "")
    if mark and hmac.compare_digest(mark, RELAY_KEY):
        return "relay:" + request.headers.get("X-DS-Relay-IP", "")[:64]
    told = next((request.headers[h] for h in ("X-Forwarded-For", "X-Real-IP", "Forwarded") if request.headers.get(h)), "")
    try:
        near = ipaddress.ip_address(remote)
        from_proxy = near.is_loopback or near.is_private
    except ValueError:
        from_proxy = False
    if not told or not from_proxy:
        return remote
    last = told.split(",")[-1].strip()[:64]
    trusted = os.environ.get("DS_TRUST_PROXY", "").strip() in ("1", "yes", "on", "true")
    if trusted and request.headers.get("X-Forwarded-For") and not _is_loopback(last):
        return last
    return "proxied:" + last
