"""The time pass's reward (dev/Roadmap-7.md): AdMob's server-side verification. Once a rewarded ad's been watched to its
end, Google calls /api/pass/reward with what was watched, signed (ECDSA, P-256 with SHA-256) by one of its keys
(KEYS_URL); only a reward Google signed counts, never the app's word. The app gave the ad the account's one-off key
(custom_data: central/app.py pass_start), so the reward is that account's, and counts once.

Set up by DS_ADMOB_REWARDED (the rewarded ad unit's id, ca-app-pub-.../...: its callback URL in AdMob is this server's
/api/pass/reward). The signature's checked here with the standard library (no crypto package on a phone or a VM)."""
import base64
import hashlib
import logging
import os
import time
from urllib.parse import parse_qs

from .bought import ask, der, der_items, Refused

log = logging.getLogger("ashen.central")

KEYS_URL = "https://www.gstatic.com/admob/reward/verifier-keys.json"
KEYS_DAY = 86400                    # (Google's keys asked for again after a day; an unknown one, sooner)
KEYS_AGAIN = 600
OLDEST = 3600                       # (a reward older than an hour isn't taken: seconds)
_keys = {"keys": {}, "at": 0.0, "tried": 0.0}

# P-256 (secp256r1)
P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
A = P - 3
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
     0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)


def ready():
    return bool(os.environ.get("DS_ADMOB_REWARDED", "").strip())


def on_curve(q):
    return q is not None and 0 <= q[0] < P and 0 <= q[1] < P and (q[1] * q[1] - q[0] ** 3 - A * q[0] - B) % P == 0


def add(p, q):
    """Two points' sum (None: the point at infinity)."""
    if p is None:
        return q
    if q is None:
        return p
    if p[0] == q[0] and (p[1] + q[1]) % P == 0:
        return None
    if p == q:
        k = (3 * p[0] * p[0] + A) * pow(2 * p[1], -1, P) % P
    else:
        k = (q[1] - p[1]) * pow(q[0] - p[0], -1, P) % P
    x = (k * k - p[0] - q[0]) % P
    return x, (k * (p[0] - x) - p[1]) % P


def times(k, p):
    out = None
    while k:
        if k & 1:
            out = add(out, p)
        p, k = add(p, p), k >> 1
    return out


def public_key(pem_or_b64):
    """(x, y) from a public key's PEM or base64 (SubjectPublicKeyInfo: the point, uncompressed)."""
    body = base64.b64decode("".join(line for line in str(pem_or_b64).strip().splitlines()
                                    if not line.startswith("-----")))
    bits = der_items(der(body)[1])[1][1]
    if len(bits) != 66 or bits[1] != 4:
        raise ValueError("not an uncompressed P-256 point")
    q = int.from_bytes(bits[2:34], "big"), int.from_bytes(bits[34:], "big")
    if not on_curve(q):
        raise ValueError("not on P-256")
    return q


def verify(q, message, signature):
    """Whether signature (DER: r and s) is q's ECDSA signature of message, with SHA-256."""
    try:
        r, s = (int.from_bytes(v, "big") for _, v in der_items(der(signature)[1])[:2])
    except (IndexError, ValueError):
        return False
    if not (0 < r < N and 0 < s < N):
        return False
    e = int.from_bytes(hashlib.sha256(message).digest(), "big")
    w = pow(s, -1, N)
    point = add(times(e * w % N, G), times(r * w % N, q))
    return point is not None and point[0] % N == r


async def keys(key_id):
    """Google's key key_id, asked for when they're a day old or it isn't known (not more than every few minutes)."""
    now = time.time()
    have = _keys["keys"]
    if (key_id not in have and now - _keys["tried"] > KEYS_AGAIN) or now - _keys["at"] > KEYS_DAY:
        _keys["tried"] = now
        status, got = await ask("GET", KEYS_URL)
        found = {}
        for k in got.get("keys") or []:
            try:
                found[str(k["keyId"])] = public_key(k.get("base64") or k["pem"])
            except (KeyError, IndexError, ValueError, TypeError):
                continue
        if status == 200 and found:
            _keys.update(keys=found, at=now)
            have = found
        else:
            log.warning("AdMob's keys couldn't be had: %s", status)
    return have.get(str(key_id))


async def check(query):
    """A reward's fields (custom_data, user_id, transaction_id, ...) from AdMob's callback, its raw query string, once
    its signature's checked; or Refused."""
    query = str(query)
    cut = query.find("&signature=")
    if cut < 0:
        raise Refused("No signature.")
    got = {k: v[0] for k, v in parse_qs(query, keep_blank_values=True).items()}
    q = await keys(got.get("key_id", ""))
    if q is None:
        raise Refused("Not a key of Google's.")
    try:
        sig = base64.urlsafe_b64decode(got.get("signature", "") + "=" * (-len(got.get("signature", "")) % 4))
    except ValueError:
        raise Refused("Not a signature.") from None
    if not verify(q, query[:cut].encode(), sig):
        raise Refused("The signature doesn't match.")
    try:
        when = int(got.get("timestamp", "0")) / 1000
    except ValueError:
        when = 0
    if abs(time.time() - when) > OLDEST:
        raise Refused("That reward is too old.")
    unit = os.environ.get("DS_ADMOB_REWARDED", "").strip()
    if got.get("ad_unit") and got["ad_unit"] not in (unit, unit.rsplit("/", 1)[-1]):
        raise Refused("Not this game's ad.")
    return got


def sign(d, message, k):
    """(for the tests: a signature as Google's are, by the private key d, k a one-off number)"""
    r = times(k, G)[0] % N
    s = pow(k, -1, N) * (int.from_bytes(hashlib.sha256(message).digest(), "big") + r * d) % N

    def integer(v):
        b = v.to_bytes((v.bit_length() + 8) // 8, "big")
        return b"\x02" + bytes([len(b)]) + b
    body = integer(r) + integer(s)
    return base64.urlsafe_b64encode(b"\x30" + bytes([len(body)]) + body).rstrip(b"=").decode()


def spki(q):
    """(for the tests: a public key as Google's keys file has it, base64)"""
    point = b"\x04" + q[0].to_bytes(32, "big") + q[1].to_bytes(32, "big")
    alg = bytes.fromhex("301306072a8648ce3d020106082a8648ce3d030107")
    bits = b"\x03" + bytes([len(point) + 1]) + b"\x00" + point
    body = alg + bits
    return base64.b64encode(b"\x30" + bytes([len(body)]) + body).decode()

