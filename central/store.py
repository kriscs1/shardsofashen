"""The central server's database (SQLite): accounts, their log-in tokens, the one-time tickets that take a player into
a game server, and the remote servers that announce themselves."""
import hashlib
import os
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    password TEXT NOT NULL,
    recover TEXT NOT NULL DEFAULT '',
    made REAL NOT NULL,
    banned TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    ticket TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    server TEXT NOT NULL,
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS servers (
    key TEXT PRIMARY KEY,
    secret TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    online INTEGER NOT NULL DEFAULT 0,
    max INTEGER NOT NULL DEFAULT 0,
    version TEXT NOT NULL DEFAULT '',
    seen REAL NOT NULL
);
"""
TOKEN_DAYS = 30
TICKET_SECONDS = 120
SERVER_SECONDS = 180            # (a remote server not heard from for this long isn't listed)


def digest(secret):
    """What's kept of a token or a ticket: its hash (a stolen database can't log anyone in)."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def new_secret():
    return os.urandom(24).hex()


class CentralStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.executescript(SCHEMA)

    # ----- accounts
    def account(self, name):
        """(name as made, password hash, recovery hash, banned why) or None."""
        return self.db.execute("SELECT name, password, recover, banned FROM accounts WHERE name = ?", (name,)).fetchone()

    def create_account(self, name, pw_hash, recover_hash):
        self.db.execute("INSERT INTO accounts (name, password, recover, made) VALUES (?, ?, ?, ?)",
                        (name, pw_hash, recover_hash, time.time()))

    def set_password(self, name, pw_hash):
        self.db.execute("UPDATE accounts SET password = ? WHERE name = ?", (pw_hash, name))
        self.db.execute("DELETE FROM tokens WHERE name = ?", (name,))      # (logged out everywhere)

    def set_recover(self, name, recover_hash):
        self.db.execute("UPDATE accounts SET recover = ? WHERE name = ?", (recover_hash, name))

    def set_banned(self, name, why):
        self.db.execute("UPDATE accounts SET banned = ? WHERE name = ?", (why, name))

    def count_accounts(self):
        return self.db.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    # ----- log-in tokens (kept by the app or browser: no password each time)
    def new_token(self, name):
        token = new_secret()
        self.db.execute("INSERT INTO tokens (token, name, made) VALUES (?, ?, ?)", (digest(token), name, time.time()))
        return token

    def token_name(self, token):
        row = self.db.execute("SELECT name, made FROM tokens WHERE token = ?", (digest(str(token)),)).fetchone()
        if not row or time.time() - row[1] > TOKEN_DAYS * 86400:
            return None
        return row[0]

    def drop_token(self, token):
        self.db.execute("DELETE FROM tokens WHERE token = ?", (digest(str(token)),))

    # ----- tickets: one game server, once, soon
    def new_ticket(self, name, server):
        ticket = new_secret()
        self.db.execute("INSERT INTO tickets (ticket, name, server, made) VALUES (?, ?, ?, ?)",
                        (digest(ticket), name, server, time.time()))
        return ticket

    def use_ticket(self, ticket, server):
        """The player's name if ticket is good for this server (it's used up either way), else None."""
        key = digest(str(ticket))
        row = self.db.execute("SELECT name, server, made FROM tickets WHERE ticket = ?", (key,)).fetchone()
        self.db.execute("DELETE FROM tickets WHERE ticket = ? OR made < ?", (key, time.time() - TICKET_SECONDS))
        if not row or row[1] != server or time.time() - row[2] > TICKET_SECONDS:
            return None
        return row[0]

    # ----- remote servers
    def announce(self, key, secret, name, url, online, most, version):
        """A remote server says it's there (key and secret: its own, from the first time). Returns (key, secret)."""
        row = self.db.execute("SELECT secret FROM servers WHERE key = ?", (key,)).fetchone() if key else None
        if row is None or row[0] != digest(secret or ""):
            # (new: its own id if it has one nobody holds - what tickets are made out to - else one given it)
            fresh = key and row is None and len(key) == 16 and all(ch in "0123456789abcdef" for ch in key)
            key, secret = (key if fresh else new_secret()[:16]), new_secret()
            self.db.execute("INSERT INTO servers (key, secret, name, url, online, max, version, seen) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (key, digest(secret), name, url, online, most, version, time.time()))
        else:
            self.db.execute("UPDATE servers SET name = ?, url = ?, online = ?, max = ?, version = ?, seen = ? "
                            "WHERE key = ?", (name, url, online, most, version, time.time(), key))
        return key, secret

    def goodbye(self, key, secret):
        self.db.execute("UPDATE servers SET seen = 0 WHERE key = ? AND secret = ?", (key, digest(secret or "")))

    def servers(self):
        rows = self.db.execute("SELECT key, name, url, online, max, version FROM servers WHERE seen > ? "
                               "ORDER BY online DESC, name", (time.time() - SERVER_SECONDS,)).fetchall()
        return [{"key": k, "name": n, "url": u, "online": o, "max": m, "version": v} for k, n, u, o, m, v in rows]
