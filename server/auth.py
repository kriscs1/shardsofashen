"""Passwords: scrypt (the standard library's), stored as scrypt$n$r$p$salt$hash."""
import base64
import hashlib
import hmac
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


def clean_name(entered):
    """A character's name as the desktop game allowed them: letters, digits, space, _ and -, at most 20."""
    name = "".join(c for c in str(entered) if c in NAME_CHARS).strip(" ")[:20]
    return "" if name.upper() == "TEMPLATE" else name
