"""Owning the game: a purchase is checked with the store it was bought from before it counts on the account, never taken
on an app's word. Each store is set up by its settings (README-Server.md "Owning the game"); one that isn't says so.

  Google Play (the Android app's full-game product): its purchase token, asked of the Play Developer API as a service
      account (DS_PLAY_SERVICE_ACCOUNT, its JSON key file; DS_PLAY_PACKAGE, DS_FULL_PRODUCT). The token for that API is
      a JWT signed with the account's RSA key, signed here (standard library: no crypto package on a phone or a VM).
  Steam (the desktop app's session ticket for the Web API): who it is, then that they own the app themselves (a game
      lent by Family Sharing isn't theirs). DS_STEAM_KEY (a publisher Web API key), DS_STEAM_APP.
  itch.io: the download key on their purchase's page (the link, or the key), asked of itch.io's API; or, bought from
      the website's Buy (DS_BUY_URL), the purchase made with the account's confirmed email (never an email the player
      gives: app.py puts it in). DS_ITCH_KEY (an API key), DS_ITCH_GAME (the game's id).

Play Integrity (integrity()): that the Android app asking is the one from Google Play, untouched, on a real device that
passes Google's checks, decoded by Google with the same service account (README-Server.md "Owning the game").

check() gives the store's own id for the purchase (Play's purchase token, the Steam id, the itch.io key's id): the
account keeps only its hash (store.claim), so one purchase is only ever one account's."""
import base64
import hashlib
import json
import logging
import os
import time

log = logging.getLogger("ashen.central")

PLAY_API = "https://androidpublisher.googleapis.com/androidpublisher/v3"
PLAY_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
INTEGRITY_API = "https://playintegrity.googleapis.com/v1"
INTEGRITY_SCOPE = "https://www.googleapis.com/auth/playintegrity"
INTEGRITY_OLDEST = 600              # (seconds a verdict is good for after it was asked for)
TOKEN_URL = "https://oauth2.googleapis.com/token"
STEAM_API = "https://partner.steam-api.com"
STEAM_IDENTITY = "shardsofashen"    # (what the desktop app's ticket is asked for: GetAuthTicketForWebApi's identity)
ITCH_API = "https://itch.io/api/1"
STORES = ("play", "steam", "itch")
_play_token = {}                    # (scope: [a Google API's access token, when it runs out])


class Refused(Exception):
    """The purchase can't be taken: what to tell the player."""


def env(name, default=""):
    return os.environ.get(name, default).strip()


def ready():
    """The stores this central server can check a purchase with."""
    return {"play": bool(env("DS_PLAY_SERVICE_ACCOUNT")), "steam": bool(env("DS_STEAM_KEY") and env("DS_STEAM_APP")),
            "itch": bool(env("DS_ITCH_KEY") and env("DS_ITCH_GAME"))}


async def check(where, proof):
    """The store's own id for a purchase of the full game, or Refused."""
    if where not in STORES:
        raise Refused("That isn't a store the game is sold in.")
    if not ready()[where]:
        raise Refused("This server can't check a purchase from there yet.")
    proof = proof if isinstance(proof, dict) else {}
    return await {"play": play, "steam": steam, "itch": itch}[where](proof)


async def ask(method, url, **kw):
    """(status, JSON) from a store's API, or Refused if it couldn't be reached."""
    import aiohttp
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http:
            async with http.request(method, url, **kw) as r:
                text = await r.text()
                try:
                    got = json.loads(text) if text.strip() else {}
                except ValueError:
                    got = {}
                return r.status, got if isinstance(got, dict) else {}
    except (aiohttp.ClientError, TimeoutError) as e:
        log.warning("A store couldn't be reached: %s", e)
        raise Refused("The store couldn't be reached just now: try again.") from None


# ----- Google Play
def der(data, i=0):
    """One DER item at i: (tag, its value's bytes, where the next one starts)."""
    tag, n = data[i], data[i + 1]
    i += 2
    if n & 0x80:
        k = n & 0x7F
        n = int.from_bytes(data[i:i + k], "big")
        i += k
    return tag, data[i:i + n], i + n


def der_items(data):
    items, i = [], 0
    while i < len(data):
        tag, value, i = der(data, i)
        items.append((tag, value))
    return items


def rsa_key(pem):
    """(n, d) from an RSA private key's PEM (PKCS#8, as a service account's is, or PKCS#1)."""
    body = base64.b64decode("".join(line for line in str(pem).strip().splitlines() if not line.startswith("-----")))
    items = der_items(der(body)[1])
    if len(items) >= 3 and items[1][0] == 0x30 and items[2][0] == 0x04:     # (PKCS#8: the PKCS#1 key inside)
        items = der_items(der(items[2][1])[1])
    return int.from_bytes(items[1][1], "big"), int.from_bytes(items[3][1], "big")


SHA256_INFO = bytes.fromhex("3031300d060960864801650304020105000420")       # (DigestInfo's start for SHA-256)


def rsa_sign(key, data):
    """RSASSA-PKCS1-v1_5 with SHA-256 (JWT's RS256)."""
    n, d = key
    k = (n.bit_length() + 7) // 8
    t = SHA256_INFO + hashlib.sha256(data).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(k, "big")


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def assertion(account, now, scope=PLAY_SCOPE):
    """The service account's signed JWT, asking for a Google API (the Play Developer API, or Play Integrity's)."""
    head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64(json.dumps({"iss": account["client_email"], "scope": scope, "aud": TOKEN_URL, "iat": int(now),
                             "exp": int(now) + 3600}).encode())
    signed = (head + "." + claims).encode()
    return head + "." + claims + "." + b64(rsa_sign(rsa_key(account["private_key"]), signed))


async def play_token(scope=PLAY_SCOPE):
    kept = _play_token.get(scope)
    if kept and time.time() < kept[1] - 60:
        return kept[0]
    try:
        with open(env("DS_PLAY_SERVICE_ACCOUNT"), encoding="utf-8") as f:
            account = json.load(f)
        jwt = assertion(account, time.time(), scope)
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        log.warning("The Google Play service account's key (DS_PLAY_SERVICE_ACCOUNT) couldn't be read")
        raise Refused("This server can't ask Google Play just now: try again later.") from None
    status, got = await ask("POST", TOKEN_URL, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                                     "assertion": jwt})
    if status != 200 or not got.get("access_token"):
        log.warning("Google refused the Play service account: %s", got.get("error") or status)
        raise Refused("This server can't ask Google Play just now: try again later.")
    _play_token[scope] = [got["access_token"], time.time() + float(got.get("expires_in") or 3600)]
    return got["access_token"]


async def play(proof):
    token = str(proof.get("token", ""))[:600]
    if not token or any(not (ch.isascii() and (ch.isalnum() or ch in "._-")) for ch in token):
        raise Refused("That isn't a Google Play purchase.")    # (nothing that would make another address: "../")
    package = env("DS_PLAY_PACKAGE", "io.github.kriscs1.shardsofashen")
    url = "%s/applications/%s/purchases/products/%s/tokens/%s" % (PLAY_API, package, env("DS_FULL_PRODUCT", "full_game"),
                                                                  token)
    auth = {"Authorization": "Bearer " + await play_token()}
    status, got = await ask("GET", url, headers=auth)
    if status != 200 or got.get("kind") != "androidpublisher#productPurchase" or "purchaseState" not in got:
        raise Refused("Google Play doesn't know that purchase.")   # (a purchase's answer, saying so: nothing else counts)
    if got.get("purchaseState") != 0:        # (0 bought; 1 cancelled or refunded; 2 still being paid for)
        raise Refused("That purchase isn't paid for yet." if got.get("purchaseState") == 2
                      else "That purchase was cancelled.")
    if got.get("acknowledgementState", 1) == 0:     # (Google refunds one not acknowledged within three days)
        await ask("POST", url + ":acknowledge", headers=auth, json={})
    return token


async def play_voided(since):
    """The purchase tokens Google Play has voided (refunded, charged back, cancelled) since then (seconds), every page
    of them: a refund takes the full game back (app.py recheck_refunds). Refused if Play can't be asked."""
    package = env("DS_PLAY_PACKAGE", "io.github.kriscs1.shardsofashen")
    url = "%s/applications/%s/purchases/voidedpurchases" % (PLAY_API, package)
    auth = {"Authorization": "Bearer " + await play_token()}
    params, out = {"startTime": str(int(since * 1000)), "maxResults": "1000"}, []
    for _ in range(100):                            # (pages: never for ever)
        status, got = await ask("GET", url, headers=auth, params=params)
        if status != 200:
            raise Refused("Google Play's voided purchases couldn't be read (%s)." % status)
        out += [str(v["purchaseToken"]) for v in got.get("voidedPurchases") or [] if v.get("purchaseToken")]
        more = (got.get("tokenPagination") or {}).get("nextPageToken")
        if not more:
            break
        params["token"] = more
    return out


def integrity_on():
    """Whether the Android app must show Play Integrity's verdict (for a time pass): DS_PLAY_INTEGRITY=1, and the
    service account to decode it with."""
    return env("DS_PLAY_INTEGRITY") == "1" and bool(env("DS_PLAY_SERVICE_ACCOUNT"))


async def integrity(token, nonce):
    """Play Integrity's verdict (the app's token, asked for with this nonce), decoded by Google: Refused unless it's
    this game from Google Play, untouched, on a device that meets Google's integrity, asked for just now."""
    token = str(token or "")[:8000]
    if not token or not nonce:
        raise Refused("The app couldn't show it's the real one from Google Play: update it from there.")
    package = env("DS_PLAY_PACKAGE", "io.github.kriscs1.shardsofashen")
    auth = {"Authorization": "Bearer " + await play_token(INTEGRITY_SCOPE)}
    status, got = await ask("POST", "%s/%s:decodeIntegrityToken" % (INTEGRITY_API, package), headers=auth,
                            json={"integrity_token": token})
    v = got.get("tokenPayloadExternal") if status == 200 else None
    if not isinstance(v, dict):
        log.warning("Play Integrity didn't decode a token: %s", status)
        raise Refused("The app couldn't show it's the real one from Google Play: update it from there.")
    asked = v.get("requestDetails") or {}
    app = (v.get("appIntegrity") or {}).get("appRecognitionVerdict", "")
    device = (v.get("deviceIntegrity") or {}).get("deviceRecognitionVerdict") or []
    try:
        age = time.time() - int(asked.get("timestampMillis", 0)) / 1000
    except (TypeError, ValueError):
        age = INTEGRITY_OLDEST + 1
    if asked.get("requestPackageName") != package or asked.get("nonce") != nonce or not -60 < age < INTEGRITY_OLDEST:
        raise Refused("That check wasn't this one: try again.")
    if app != "PLAY_RECOGNIZED":                    # (UNRECOGNIZED_VERSION: changed, or not from Google Play)
        raise Refused("This copy of the app isn't the one from Google Play: install it from there.")
    if "MEETS_DEVICE_INTEGRITY" not in device:      # (an emulator, a rooted phone, a tampered one)
        raise Refused("A time pass needs a phone that passes Google Play's checks (not an emulator or a rooted one).")
    return v


# ----- Steam
async def steam(proof):
    ticket = str(proof.get("ticket", ""))[:2048]
    if not ticket or any(ch not in "0123456789abcdefABCDEF" for ch in ticket):
        raise Refused("That isn't a Steam ticket.")
    key, app = env("DS_STEAM_KEY"), env("DS_STEAM_APP")
    status, got = await ask("GET", STEAM_API + "/ISteamUserAuth/AuthenticateUserTicket/v1/",
                            params={"key": key, "appid": app, "ticket": ticket, "identity": STEAM_IDENTITY})
    who = (got.get("response") or {}).get("params") or {}
    if status != 200 or who.get("result") != "OK" or not who.get("steamid"):
        raise Refused("Steam didn't know that ticket: start the game from Steam and try again.")
    if who.get("ownersteamid") and who["ownersteamid"] != who["steamid"]:
        raise Refused("That copy is lent through Family Sharing: it's its owner's.")
    status, got = await ask("GET", STEAM_API + "/ISteamUser/CheckAppOwnership/v4/",
                            params={"key": key, "steamid": who["steamid"], "appid": app})
    owns = got.get("appownership") or {}
    if status != 200 or not owns.get("ownsapp") or (owns.get("ownersteamid") or who["steamid"]) != who["steamid"]:
        raise Refused("That Steam account doesn't own the game.")
    return str(who["steamid"])


# ----- itch.io
async def itch(proof):
    email = str(proof.get("email", "")).strip()[:200]
    if email:                                   # (the same download key a pasted link gives: one purchase, one account)
        params, unknown = {"email": email}, ("itch.io has no purchase made with your account's email (%s): paste the "
                                             "link from your purchase's page in Account instead." % email)
    else:
        key = str(proof.get("key", "")).strip().rstrip("/").rsplit("/", 1)[-1].split("?")[0][:100]
        if not key or not all(ch.isalnum() or ch in "-_" for ch in key):
            raise Refused("That isn't an itch.io download key: paste the link from your purchase's page.")
        params, unknown = {"download_key": key}, "itch.io doesn't know that download key."
    status, got = await ask("GET", "%s/%s/game/%s/download_keys" % (ITCH_API, env("DS_ITCH_KEY"), env("DS_ITCH_GAME")),
                            params=params)
    found = got.get("download_key") or {}
    if status != 200 or not found.get("id") or str(found.get("game_id", env("DS_ITCH_GAME"))) != env("DS_ITCH_GAME"):
        raise Refused(unknown)
    return str(found["id"])


def buy_page():
    """The website's Buy: the game's page on itch.io (DS_BUY_URL) and its price as shown (DS_BUY_PRICE), or None."""
    url = env("DS_BUY_URL")
    if not (url.startswith("https://") and ready()["itch"]):
        return None
    return {"url": url, "price": env("DS_BUY_PRICE")[:20]}
