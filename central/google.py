"""Signing in with Google: OAuth 2.0's code flow with PKCE, all on this server (Google's own button and script can't work
in the apps: Google refuses to sign in inside an app's web view, so the apps open it in the phone's or PC's browser, and
the same pages serve a browser too). Set DS_GOOGLE_CLIENT_ID and DS_GOOGLE_CLIENT_SECRET (README-Server.md says how);
without them the start screen shows no such button. Only "openid email" is asked for: who it is, and their address."""
import base64
import binascii
import hashlib
import json
import logging
import os
import secrets
import time
from urllib.parse import urlencode

log = logging.getLogger("ashen.central")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
FLOW_SECONDS = 600                  # (from setting off to coming back from Google)
RESULT_SECONDS = 900                # (from coming back to the start screen taking it: time to type a code, choose a name)
LEEWAY = 60                         # (seconds a clock may be out)


class Refused(Exception):
    """Google's answer can't be taken: what to tell the player."""


def client():
    return os.environ.get("DS_GOOGLE_CLIENT_ID", "").strip(), os.environ.get("DS_GOOGLE_CLIENT_SECRET", "").strip()


def ready():
    return all(client())


def new_flow(to):
    """One sign-in's secrets: state (ties Google's answer to this browser), nonce (ties its token to this sign-in),
    verifier (PKCE: only this server can use the code Google gives)."""
    return {"state": secrets.token_urlsafe(24), "nonce": secrets.token_urlsafe(24), "verifier": secrets.token_urlsafe(48),
            "to": to, "at": time.time()}


def auth_url(redirect, flow):
    challenge = base64.urlsafe_b64encode(hashlib.sha256(flow["verifier"].encode()).digest()).rstrip(b"=").decode()
    return AUTH_URL + "?" + urlencode({"client_id": client()[0], "redirect_uri": redirect, "response_type": "code",
                                       "scope": "openid email", "state": flow["state"], "nonce": flow["nonce"],
                                       "code_challenge": challenge, "code_challenge_method": "S256",
                                       "prompt": "select_account"})


def read_id_token(token, nonce, now=None):
    """(Google's id for them, their address) from an ID token that came straight from Google's token endpoint over TLS
    (so OpenID Connect doesn't ask for its signature to be checked): that it's for this app, this sign-in, not run out,
    and that Google has verified the address."""
    now = time.time() if now is None else now
    try:
        body = str(token).split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (IndexError, ValueError, binascii.Error):
        raise Refused("Google's answer couldn't be read.") from None
    if not isinstance(claims, dict):
        raise Refused("Google's answer couldn't be read.")
    if claims.get("iss") not in ISSUERS or claims.get("aud") != client()[0]:
        raise Refused("That sign-in wasn't for this game.")
    if not secrets.compare_digest(str(claims.get("nonce", "")).encode("utf-8"), nonce.encode("utf-8")):
        raise Refused("That sign-in wasn't for this game.")
    try:
        if float(claims.get("exp", 0)) < now - LEEWAY:
            raise Refused("That sign-in has run out: try again.")
    except (TypeError, ValueError):
        raise Refused("Google's answer couldn't be read.") from None
    sub, email = str(claims.get("sub", "")), str(claims.get("email", ""))
    if not sub or not email:
        raise Refused("Google didn't say who that is.")
    if claims.get("email_verified") not in (True, "true"):
        raise Refused("Google hasn't verified that account's email.")
    return sub[:255], email


async def sign_in(code, redirect, flow):
    """Google's code for this sign-in, swapped for who it is: (Google's id for them, their address)."""
    import aiohttp
    cid, secret = client()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as http:
            async with http.post(TOKEN_URL, data={"grant_type": "authorization_code", "code": code, "client_id": cid,
                                                  "client_secret": secret, "redirect_uri": redirect,
                                                  "code_verifier": flow["verifier"]}) as r:
                got = await r.json(content_type=None)
                if r.status != 200 or not isinstance(got, dict) or not got.get("id_token"):
                    log.warning("Google refused a sign-in: %s", (got or {}).get("error") if isinstance(got, dict) else r.status)
                    raise Refused("Google didn't accept that sign-in: try again.")
    except (aiohttp.ClientError, TimeoutError, ValueError) as e:
        log.warning("Google couldn't be reached: %s", e)
        raise Refused("Google couldn't be reached just now: try again.") from None
    return read_id_token(got["id_token"], flow["nonce"])
