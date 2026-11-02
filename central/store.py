"""The central server's database (SQLite): accounts, their log-in tokens, the one-time tickets that take a player into
a game server, the remote servers that announce themselves, and friends: who asked whom (both ways: friends), the
keys a game server is given to a player's friends while they play there, and where each account is playing."""
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
CREATE TABLE IF NOT EXISTS mailchecks (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    email TEXT NOT NULL,
    token TEXT NOT NULL DEFAULT '',
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS friends (
    who TEXT NOT NULL COLLATE NOCASE,
    whom TEXT NOT NULL COLLATE NOCASE,
    made REAL NOT NULL,
    PRIMARY KEY (who, whom)
);
CREATE TABLE IF NOT EXISTS grants (
    token TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    server TEXT NOT NULL,
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS playing (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    server TEXT NOT NULL,
    place TEXT NOT NULL,
    character TEXT NOT NULL,
    seen REAL NOT NULL
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
CONFIRM_DAYS = 3                # (a link to confirm an email works this long)
UNCONFIRMED_DAYS = 30           # (an email nobody confirmed is forgotten after this)
TOKEN_DAYS = 30
TICKET_SECONDS = 120
SERVER_SECONDS = 180            # (a remote server not heard from for this long isn't listed)
GRANT_DAYS = 2                  # (a game server's key to a player's friends: while they play there, and a while after)
PLAYING_SECONDS = 300           # (playing somewhere: as long as their game says so this often)
MOST_FRIENDS = 200


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
        waiting = "(SELECT email FROM mailchecks WHERE mailchecks.name = accounts.name)"
        return self.db.execute("SELECT name, email, banned, admin, made, COALESCE(%s, '') FROM accounts WHERE name LIKE ? "
                               "OR email LIKE ? OR %s LIKE ? ORDER BY made DESC LIMIT ?" % (waiting, waiting),
                               (like, like, like, limit)).fetchall()

    # ----- an email waiting to be confirmed (accounts.email is only ever one that has been)
    def set_pending_email(self, name, email):
        self.db.execute("INSERT OR REPLACE INTO mailchecks (name, email, token, made) VALUES (?, ?, '', ?)",
                        (name, email, time.time()))

    def pending_email(self, name):
        row = self.db.execute("SELECT email FROM mailchecks WHERE name = ?", (name,)).fetchone()
        return row[0] if row else ""

    def new_mail_check(self, name):
        """A new link's secret for what's waiting (the last link's no good after this)."""
        token = new_secret()
        self.db.execute("UPDATE mailchecks SET token = ?, made = ? WHERE name = ?", (digest(token), time.time(), name))
        return token

    def mail_check(self, token):
        """(name, email) that a link's secret confirms, if it's good."""
        if not token:
            return None
        row = self.db.execute("SELECT name, email, made FROM mailchecks WHERE token = ?", (digest(str(token)),)).fetchone()
        if not row or time.time() - row[2] > CONFIRM_DAYS * 86400:
            return None
        return row[0], row[1]

    def drop_mail_check(self, name):
        self.db.execute("DELETE FROM mailchecks WHERE name = ?", (name,))

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

    # ----- friends: who asked whom (an ask both ways: friends)
    def ask_friend(self, who, whom):
        """who asks whom: "friends" (whom had asked: now both are), "asked", or "already"."""
        if self.db.execute("SELECT 1 FROM friends WHERE who = ? AND whom = ?", (who, whom)).fetchone():
            return "already"
        self.db.execute("INSERT INTO friends (who, whom, made) VALUES (?, ?, ?)", (who, whom, time.time()))
        back = self.db.execute("SELECT 1 FROM friends WHERE who = ? AND whom = ?", (whom, who)).fetchone()
        return "friends" if back else "asked"

    def drop_friend(self, who, whom):
        """Friends no more, or an ask taken back or turned down: both ways."""
        self.db.execute("DELETE FROM friends WHERE (who = ? AND whom = ?) OR (who = ? AND whom = ?)",
                        (who, whom, whom, who))

    def friend_lists(self, name):
        """(friends, asking: asked name, asked: name asked) - names as their accounts were made."""
        out = self.db.execute("SELECT a.name FROM friends f JOIN accounts a ON a.name = f.whom WHERE f.who = ?",
                              (name,)).fetchall()
        inn = self.db.execute("SELECT a.name FROM friends f JOIN accounts a ON a.name = f.who WHERE f.whom = ?",
                              (name,)).fetchall()
        out, inn = {r[0] for r in out}, {r[0] for r in inn}
        key = str.lower
        return sorted(out & inn, key=key), sorted(inn - out, key=key), sorted(out - inn, key=key)

    def asked_count(self, name):
        return self.db.execute("SELECT COUNT(*) FROM friends WHERE who = ?", (name,)).fetchone()[0]

    # ----- a game server's key to a player's friends (given with the ticket: only their friends, only from there)
    def new_grant(self, name, server):
        token = new_secret()
        self.db.execute("INSERT INTO grants (token, name, server, made) VALUES (?, ?, ?, ?)",
                        (digest(token), name, server, time.time()))
        return token

    def grant_name(self, token):
        """(name, server) for a game server's key, or None. Each use keeps it good a while longer."""
        key = digest(str(token))
        row = self.db.execute("SELECT name, server, made FROM grants WHERE token = ?", (key,)).fetchone()
        if not row or time.time() - row[2] > GRANT_DAYS * 86400:
            return None
        self.db.execute("UPDATE grants SET made = ? WHERE token = ?", (time.time(), key))
        return row[0], row[1]

    # ----- where everyone's playing (their game says so while they play)
    def set_playing(self, name, server, place, character):
        if character:
            self.db.execute("INSERT OR REPLACE INTO playing (name, server, place, character, seen) VALUES (?, ?, ?, ?, ?)",
                            (name, server, place, character, time.time()))
        else:
            self.db.execute("DELETE FROM playing WHERE name = ? AND server = ?", (name, server))

    def playing_of(self, names):
        """{name: {"server", "place", "character", "url"}} for those of names playing just now (url: a listed game's)."""
        out = {}
        for n in names:
            row = self.db.execute("SELECT p.server, p.place, p.character, s.url, s.approved FROM playing p LEFT JOIN "
                                  "servers s ON s.key = p.server WHERE p.name = ? AND p.seen > ?",
                                  (n, time.time() - PLAYING_SECONDS)).fetchone()
            if row:
                out[n] = {"server": row[0], "place": row[1], "character": row[2], "url": row[3] if row[4] else ""}
        return out

    # ----- remote servers
    def announce(self, key, secret, name, url, online, most, version):
        """A remote server says it's there (key and secret: its own, from the first time). Returns (key, secret)."""
        row = self.db.execute("SELECT secret, name, url FROM servers WHERE key = ?", (key,)).fetchone() if key else None
        if row is None or row[0] != digest(secret or ""):
            # (new: its own id if it has one nobody holds - what tickets are made out to - else one given it)
            fresh = key and row is None and len(key) == 16 and all(ch in "0123456789abcdef" for ch in key)
            key, secret = (key if fresh else new_secret()[:16]), new_secret()
            self.db.execute("INSERT INTO servers (key, secret, name, url, online, max, version, seen, made) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (key, digest(secret), name, url, online, most, version, time.time(), time.time()))
        else:
            if (name, url) != (row[1], row[2]):        # (a new name or address: approved again, or a listed game
                self.set_approved(key, False)           # could become anything, anywhere)
            self.db.execute("UPDATE servers SET name = ?, url = ?, online = ?, max = ?, version = ?, seen = ? "
                            "WHERE key = ?", (name, url, online, most, version, time.time(), key))
        return key, secret

    def prune(self):
        """What's had its day: used-up tickets, old tokens, games never approved and not heard from in a week."""
        now = time.time()
        self.db.execute("DELETE FROM tickets WHERE made < ?", (now - TICKET_SECONDS,))
        self.db.execute("DELETE FROM tokens WHERE made < ?", (now - TOKEN_DAYS * 86400,))
        self.db.execute("DELETE FROM grants WHERE made < ?", (now - GRANT_DAYS * 86400,))
        self.db.execute("DELETE FROM mailchecks WHERE made < ?", (now - UNCONFIRMED_DAYS * 86400,))
        self.db.execute("DELETE FROM playing WHERE seen < ?", (now - PLAYING_SECONDS,))
        self.db.execute("DELETE FROM servers WHERE approved = 0 AND seen < ?", (now - 7 * 86400,))

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
