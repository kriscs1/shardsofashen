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
CREATE TABLE IF NOT EXISTS mailcodes (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    code TEXT NOT NULL,
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
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
# (columns added since: put on an older database as it opens)
COLUMNS = [("accounts", "email", "TEXT NOT NULL DEFAULT ''"), ("accounts", "admin", "INTEGER NOT NULL DEFAULT 0"),
           ("servers", "approved", "INTEGER NOT NULL DEFAULT 0"), ("servers", "made", "REAL NOT NULL DEFAULT 0")]
MAIL_CODE_MINUTES = 30
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
        for table, col, kind in COLUMNS:
            have = [r[1] for r in self.db.execute("PRAGMA table_info(%s)" % table)]
            if col not in have:
                self.db.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, kind))

    # ----- accounts
    def account(self, name):
        """(name as made, password hash, recovery hash, banned why, email, admin) or None."""
        return self.db.execute("SELECT name, password, recover, banned, email, admin FROM accounts WHERE name = ?",
                               (name,)).fetchone()

    def account_by_email(self, email):
        row = self.db.execute("SELECT name FROM accounts WHERE email = ? COLLATE NOCASE AND email != ''",
                              (email,)).fetchone()
        return self.account(row[0]) if row else None

    def create_account(self, name, pw_hash, recover_hash, email=""):
        self.db.execute("INSERT INTO accounts (name, password, recover, made, email) VALUES (?, ?, ?, ?, ?)",
                        (name, pw_hash, recover_hash, time.time(), email))

    def set_email(self, name, email):
        self.db.execute("UPDATE accounts SET email = ? WHERE name = ?", (email, name))

    def set_admin(self, name, on):
        self.db.execute("UPDATE accounts SET admin = ? WHERE name = ?", (1 if on else 0, name))

    def find_accounts(self, q, limit=50):
        like = "%" + q.replace("%", "") + "%"
        return self.db.execute("SELECT name, email, banned, admin, made FROM accounts WHERE name LIKE ? OR email LIKE ? "
                               "ORDER BY made DESC LIMIT ?", (like, like, limit)).fetchall()

    # ----- email codes (a forgotten password, when the account has an email)
    def new_mail_code(self, name, code_hash):
        self.db.execute("INSERT OR REPLACE INTO mailcodes (name, code, made) VALUES (?, ?, ?)",
                        (name, code_hash, time.time()))

    def mail_code(self, name):
        row = self.db.execute("SELECT code, made FROM mailcodes WHERE name = ?", (name,)).fetchone()
        if not row or time.time() - row[1] > MAIL_CODE_MINUTES * 60:
            return ""
        return row[0]

    def drop_mail_code(self, name):
        self.db.execute("DELETE FROM mailcodes WHERE name = ?", (name,))

    # ----- settings (the ads, set on the admin page)
    def setting(self, key, default=""):
        row = self.db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

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
            self.db.execute("INSERT INTO servers (key, secret, name, url, online, max, version, seen, made) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (key, digest(secret), name, url, online, most, version, time.time(), time.time()))
        else:
            self.db.execute("UPDATE servers SET name = ?, url = ?, online = ?, max = ?, version = ?, seen = ? "
                            "WHERE key = ?", (name, url, online, most, version, time.time(), key))
        return key, secret

    def server_url(self, key):
        """The address a server announced itself at, or "" (a game this server's never heard from: on a network)."""
        row = self.db.execute("SELECT url FROM servers WHERE key = ?", (key,)).fetchone()
        return row[0] if row else ""

    def goodbye(self, key, secret):
        self.db.execute("UPDATE servers SET seen = 0 WHERE key = ? AND secret = ?", (key, digest(secret or "")))

    def approved(self, key):
        row = self.db.execute("SELECT approved FROM servers WHERE key = ?", (key,)).fetchone()
        return bool(row and row[0])

    def servers(self, everyone=False):
        """The listed servers: approved on the admin page, and heard from lately (everyone: all, for the admin page)."""
        rows = self.db.execute("SELECT key, name, url, online, max, version, approved, seen FROM servers " +
                               ("" if everyone else "WHERE approved = 1 AND seen > ? ") + "ORDER BY online DESC, name",
                               () if everyone else (time.time() - SERVER_SECONDS,)).fetchall()
        return [{"key": k, "name": n, "url": u, "online": o, "max": m, "version": v, "approved": bool(a),
                 "up": seen > time.time() - SERVER_SECONDS, "seen": int(seen)} for k, n, u, o, m, v, a, seen in rows]

    def set_approved(self, key, on):
        self.db.execute("UPDATE servers SET approved = ? WHERE key = ?", (1 if on else 0, key))

    def remove_server(self, key):
        self.db.execute("DELETE FROM servers WHERE key = ?", (key,))
