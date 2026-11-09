"""Owning the PC build (dev/Roadmap-7.md): it's paid for once, up front, with no demo and never an ad. Which store it
was built for is in store.json beside the program (desktop/build_desktop.py, from DS_STORE):

  steam   Steam says, through its own library (steam_api64.dll from the Steamworks SDK, beside the program): owned by
          the Steam account it's started from, or the start screen shows only how to get it. Started outside Steam, it
          starts again from Steam. Its Web API ticket goes to the central server (central/bought.py), so the Hallisium
          account has the full game too, on a phone and in a browser.
  itch, epic  the store's own download is the purchase (it's only had once it's bought). The account has it from
          itch.io's download key, pasted into the start screen's account popup.
  (none)  a build made by hand, or run from the source: owned.

The library is called with ctypes (no package of its own): SteamAPI_InitFlat (or SteamAPI_Init, an older library),
ISteamApps' BIsSubscribed, and ISteamUser's GetAuthTicketForWebApi, its answer had by manual dispatch."""
import ctypes
import json
import os
import struct
import sys
import time

IDENTITY = b"shardsofashen"         # (central/bought.py's STEAM_IDENTITY)
TICKET_ANSWER = 168                 # (GetTicketForWebApiResponse_t: k_iSteamUserCallbacks 100 + 68)
TICKET_WAIT = 10                    # (seconds Steam has to give the ticket)
APPS = ("SteamAPI_SteamApps_v008",)
USERS = ("SteamAPI_SteamUser_v023", "SteamAPI_SteamUser_v021", "SteamAPI_SteamUser_v020")


class CallbackMsg(ctypes.Structure):
    _fields_ = [("user", ctypes.c_int32), ("callback", ctypes.c_int), ("param", ctypes.POINTER(ctypes.c_uint8)),
                ("size", ctypes.c_int)]


def settings(root):
    """store.json: {"store": "steam", "steam_app": "..."}, or {} (a build made by hand)."""
    try:
        with open(os.path.join(root, "store.json"), encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def library(root):
    """Steam's library beside the program, or None."""
    name = {"win32": "steam_api64.dll", "darwin": "libsteam_api.dylib"}.get(sys.platform, "libsteam_api.so")
    path = os.path.join(root, name)
    if not os.path.exists(path):
        return None
    try:
        return ctypes.CDLL(path)
    except OSError:
        return None


def call(lib, name, restype, *args, argtypes=None):
    fn = getattr(lib, name, None)
    if fn is None:
        return None
    fn.restype = restype
    if argtypes is not None:
        fn.argtypes = argtypes
    return fn(*args)


class Steam:
    """Steam's word: whether this account owns it (owns), and a Web API ticket for the central server (ticket, hex)."""

    def __init__(self, lib, app_id):
        self.lib, self.app_id = lib, int(app_id or 0)
        self.owns, self.ticket, self.why = False, "", ""

    def ask(self):
        lib = self.lib
        if self.app_id and call(lib, "SteamAPI_RestartAppIfNecessary", ctypes.c_bool, ctypes.c_uint32(self.app_id)):
            return "restart"                            # (started outside Steam: Steam starts it again, and this goes)
        if not self.started():
            self.why = "Steam isn't running, or isn't signed in."
            return "no"
        apps = next((call(lib, n, ctypes.c_void_p) for n in APPS if getattr(lib, n, None) is not None), None)
        self.owns = bool(apps) and bool(call(lib, "SteamAPI_ISteamApps_BIsSubscribed", ctypes.c_bool,
                                             ctypes.c_void_p(apps)))
        if not self.owns:
            self.why = "This Steam account doesn't own the game."
            return "no"
        return "yes"

    def started(self):
        if getattr(self.lib, "SteamAPI_InitFlat", None) is not None:      # (SDK 1.59 on: 0 is k_ESteamAPIInitResult_OK)
            err = ctypes.create_string_buffer(1024)
            return call(self.lib, "SteamAPI_InitFlat", ctypes.c_int, err) == 0
        return bool(call(self.lib, "SteamAPI_Init", ctypes.c_bool))

    def web_ticket(self):
        """A Web API ticket for IDENTITY, hex (central/bought.py asks Steam whose it is), or "" if none came."""
        lib = self.lib
        user = next((call(lib, n, ctypes.c_void_p) for n in USERS if getattr(lib, n, None) is not None), None)
        if not user:
            return ""
        call(lib, "SteamAPI_ManualDispatch_Init", None)
        pipe = call(lib, "SteamAPI_GetHSteamPipe", ctypes.c_int32)
        handle = call(lib, "SteamAPI_ISteamUser_GetAuthTicketForWebApi", ctypes.c_uint32, ctypes.c_void_p(user),
                      ctypes.c_char_p(IDENTITY))
        if not handle:
            return ""
        msg = CallbackMsg()
        end = time.monotonic() + TICKET_WAIT
        while time.monotonic() < end:
            call(lib, "SteamAPI_ManualDispatch_RunFrame", None, ctypes.c_int32(pipe))
            while call(lib, "SteamAPI_ManualDispatch_GetNextCallback", ctypes.c_bool, ctypes.c_int32(pipe),
                       ctypes.byref(msg)):
                got = ctypes.string_at(msg.param, msg.size) if msg.callback == TICKET_ANSWER and msg.size >= 12 else b""
                call(lib, "SteamAPI_ManualDispatch_FreeLastCallback", None, ctypes.c_int32(pipe))
                if got:
                    which, result, size = struct.unpack_from("<Iii", got)
                    if which == handle:
                        return got[12:12 + size].hex() if result == 1 and 0 < size <= len(got) - 12 else ""
            time.sleep(0.05)
        return ""


class Owning:
    """The PC build's: owned (True, False, or None while it's being asked), the store, why not, and Steam's ticket."""

    def __init__(self, root, lib=None):
        got = settings(root)
        self.root, self.store = root, str(got.get("store", ""))
        self.steam_app = str(got.get("steam_app", ""))
        self.owned, self.why, self.ticket = (None if self.store == "steam" else True), "", ""
        self.lib = lib

    def ask(self):
        """Steam's word, as the app opens: "yes", "no", or "restart" (started outside Steam: Steam starts it again,
        and this one goes). Its ticket comes after (ticket_later, in a thread: it takes a moment)."""
        if self.store != "steam":
            return "yes"
        lib = self.lib or library(self.root)
        if lib is None:
            self.owned, self.why = False, "Steam's library is missing: install the game again from Steam."
            return "no"
        self.steam = Steam(lib, self.steam_app)
        how = self.steam.ask()
        self.owned, self.why = self.steam.owns, self.steam.why
        return how

    def ticket_later(self):
        if self.owned and getattr(self, "steam", None) is not None:
            self.ticket = self.steam.web_ticket()

    def state(self):
        return {"full": self.owned, "store": self.store, "why": self.why, "steam_ticket": self.ticket}
