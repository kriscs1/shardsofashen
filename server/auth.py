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


def client_address(request):
    """Who's connecting. Behind a reverse proxy (Caddy on a cloud server, DS_TRUST_PROXY=1): the last address in
    X-Forwarded-For, the one the proxy put there (the ones before it are anyone's to write), and only when the
    connection itself is from the proxy (this machine or a private network: a port published straight to the world
    gets no say). Otherwise the connection's own address."""
    remote = request.remote or ""
    if os.environ.get("DS_TRUST_PROXY", "").strip() in ("1", "yes", "on", "true"):
        fwd = request.headers.get("X-Forwarded-For", "")
        try:
            near = ipaddress.ip_address(remote)
            from_proxy = near.is_loopback or near.is_private
        except ValueError:
            from_proxy = False
        if fwd and from_proxy:
            return fwd.split(",")[-1].strip()
    return remote
