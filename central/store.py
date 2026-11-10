"""The central server's database (SQLite): accounts, their log-in tokens, the one-time tickets that take a player into
a game server, the remote servers that announce themselves, and friends: who asked whom (both ways: friends), the
keys a game server is given to a player's friends while they play there, and where each account is playing; and what
every game server says its characters have got to (level, skills, quests), for the admin page; and owning the game:
whether each account has the full game (and where it was bought), the purchases that gave it (one purchase, one
account), and a time pass's end.

Every value in every query here goes in as a ? parameter, never into the query's text: only this file's own table and
column names are ever put in with %s (a test holds it). And once it's opened, the connection may only read and write
rows (no_schema_changes), so even a query gone wrong couldn't drop a table or reach another file."""
import hashlib
import json
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
CREATE TABLE IF NOT EXISTS reporters (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    listed INTEGER NOT NULL DEFAULT 0,
    blocked INTEGER NOT NULL DEFAULT 0,
    made REAL NOT NULL,
    seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS characters (
    server TEXT NOT NULL,
    name TEXT NOT NULL COLLATE NOCASE,
    account TEXT NOT NULL DEFAULT '' COLLATE NOCASE,
    level INTEGER NOT NULL DEFAULT 1,
    shards INTEGER NOT NULL DEFAULT 0,
    gold INTEGER NOT NULL DEFAULT 0,
    map TEXT NOT NULL DEFAULT '',
    played REAL NOT NULL DEFAULT 0,
    made REAL NOT NULL,
    seen REAL NOT NULL,
    PRIMARY KEY (server, name)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS character_skills (
    server TEXT NOT NULL,
    name TEXT NOT NULL COLLATE NOCASE,
    skill TEXT NOT NULL,
    level INTEGER NOT NULL,
    xp REAL NOT NULL,
    PRIMARY KEY (server, name, skill)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS character_quests (
    server TEXT NOT NULL,
    name TEXT NOT NULL COLLATE NOCASE,
    quest TEXT NOT NULL,
    stage INTEGER NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    began REAL NOT NULL,
    finished REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (server, name, quest)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS purchases (
    ref TEXT PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS passes (
    name TEXT NOT NULL COLLATE NOCASE,
    made REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS game_keys (
    key TEXT PRIMARY KEY,
    proof TEXT NOT NULL,
    seen REAL NOT NULL
);
"""
# (columns added since: put on an older database as it opens)
COLUMNS = [("accounts", "email", "TEXT NOT NULL DEFAULT ''"), ("accounts", "admin", "INTEGER NOT NULL DEFAULT 0"),
           ("servers", "approved", "INTEGER NOT NULL DEFAULT 0"), ("servers", "made", "REAL NOT NULL DEFAULT 0"),
           ("accounts", "deleted", "REAL NOT NULL DEFAULT 0"), ("accounts", "google", "TEXT NOT NULL DEFAULT ''"),
           ("accounts", "full", "TEXT NOT NULL DEFAULT ''"), ("accounts", "full_at", "REAL NOT NULL DEFAULT 0"),
           ("accounts", "pass_until", "REAL NOT NULL DEFAULT 0"), ("tickets", "relay", "INTEGER NOT NULL DEFAULT 0")]
# (what's looked up by something other than its key: after the columns, as some are on those)
INDEXES = """
CREATE INDEX IF NOT EXISTS accounts_email ON accounts (email COLLATE NOCASE);
CREATE UNIQUE INDEX IF NOT EXISTS accounts_google ON accounts (google) WHERE google != '';
CREATE INDEX IF NOT EXISTS accounts_made ON accounts (made);
CREATE INDEX IF NOT EXISTS tokens_name ON tokens (name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS tokens_made ON tokens (made);
CREATE INDEX IF NOT EXISTS tickets_made ON tickets (made);
CREATE INDEX IF NOT EXISTS grants_made ON grants (made);
CREATE INDEX IF NOT EXISTS grants_name ON grants (name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS friends_whom ON friends (whom);
CREATE INDEX IF NOT EXISTS mailchecks_token ON mailchecks (token);
CREATE INDEX IF NOT EXISTS servers_listed ON servers (approved, seen);
CREATE INDEX IF NOT EXISTS characters_seen ON characters (seen);
CREATE INDEX IF NOT EXISTS characters_account ON characters (account);
CREATE INDEX IF NOT EXISTS character_skills_skill ON character_skills (skill, level);
CREATE INDEX IF NOT EXISTS character_quests_quest ON character_quests (quest, done, stage);
CREATE INDEX IF NOT EXISTS purchases_name ON purchases (name);
CREATE INDEX IF NOT EXISTS passes_name ON passes (name, made);
"""
MAIL_CODE_MINUTES = 30
CONFIRM_DAYS = 3                # (a link to confirm an email works this long)
UNCONFIRMED_DAYS = 30           # (an email nobody confirmed is forgotten after this)
TOKEN_DAYS = 30
TICKET_SECONDS = 120
SERVER_SECONDS = 180            # (a remote server not heard from for this long isn't listed)
GAME_KEY_DAYS = 365             # (a game's id, proved: kept a year after it's last come in)
GRANT_DAYS = 2                  # (a game server's key to a player's friends: while they play there, and a while after)
PLAYING_SECONDS = 300           # (playing somewhere: as long as their game says so this often)
MOST_FRIENDS = 200
PROGRESS_DAYS = 365             # (a character not heard of for a year is forgotten, and a game server that has none left)
# (all the connection may do once it's open: read and write rows, in transactions)
ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
           sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


def digest(secret):
    """What's kept of a token or a ticket: its hash (a stolen database can't log anyone in)."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def new_secret():
    return os.urandom(24).hex()


def no_schema_changes(action, what, column, database, trigger):
    """SQLite's authorizer: rows may be read and written; nothing else (no DROP, ALTER, ATTACH or PRAGMA), and not
    the list of tables."""
    if action not in ALLOWED:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ and what in ("sqlite_master", "sqlite_schema", "sqlite_temp_master"):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def like(q):
    """What a search asks for, as a LIKE that means just that (with ESCAPE '\\': a name can have a _ in it)."""
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


class CentralStore:
    def __init__(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")      # (readers don't wait for a writer, and fewer disk syncs)
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        for table, col, kind in COLUMNS:
            have = [r[1] for r in self.db.execute("PRAGMA table_info(%s)" % table)]
            if col not in have:
                self.db.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, kind))
        self.db.executescript(INDEXES)
        self.db.execute("UPDATE accounts SET recover = '' WHERE recover != ''")     # (recovery codes are gone: none kept)
        self.db.set_authorizer(no_schema_changes)

    # ----- accounts
    def account(self, name):
        """(name as made, password hash, nothing now (recovery codes are gone), banned why, email, admin, when deleted
        (its name kept)) or None."""
        return self.db.execute("SELECT name, password, recover, banned, email, admin, deleted FROM accounts "
                               "WHERE name = ?", (name,)).fetchone()

    def account_by_email(self, email):
        row = self.db.execute("SELECT name FROM accounts WHERE email = ? COLLATE NOCASE AND email != ''",
                              (email,)).fetchone()
        return self.account(row[0]) if row else None

    def account_by_google(self, sub):
        """The account that signs in with this Google account (Google's own id for it, which never changes)."""
        row = self.db.execute("SELECT name FROM accounts WHERE google = ? AND google != ''", (sub,)).fetchone()
        return self.account(row[0]) if row else None

    def create_account(self, name, pw_hash, email="", google=""):
        self.db.execute("INSERT INTO accounts (name, password, made, email, google) VALUES (?, ?, ?, ?, ?)",
                        (name, pw_hash, time.time(), email, google))

    def google_of(self, name):
        row = self.db.execute("SELECT google FROM accounts WHERE name = ?", (name,)).fetchone()
        return row[0] if row else ""

    def set_email(self, name, email):
        self.db.execute("UPDATE accounts SET email = ? WHERE name = ?", (email, name))

    def set_admin(self, name, on):
        self.db.execute("UPDATE accounts SET admin = ? WHERE name = ?", (1 if on else 0, name))

    def find_accounts(self, q, limit=50, skip=0):
        found = like(q)
        waiting = "(SELECT email FROM mailchecks WHERE mailchecks.name = accounts.name)"
        return self.db.execute("SELECT name, email, banned, admin, made, COALESCE(%s, ''), deleted, google != '', full, "
                               "full_at, pass_until "
                               "FROM accounts WHERE name LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' OR %s LIKE ? "
                               "ESCAPE '\\' ORDER BY made DESC LIMIT ? OFFSET ?"
                               % (waiting, waiting), (found, found, found, limit, skip)).fetchall()

    def delete_account(self, name, keep_name):
        """All of an account's gone at once: its logins, keys, emails, friends. keep_name: its row stays, emptied, so
        nobody else can take the name (and the characters that go by it); else the name's free for anyone."""
        self.db.execute("BEGIN")
        try:
            for table in ("tokens", "tickets", "grants", "mailcodes", "mailchecks", "playing", "purchases", "passes"):
                self.db.execute("DELETE FROM %s WHERE name = ? COLLATE NOCASE" % table, (name,))
            self.db.execute("DELETE FROM friends WHERE who = ? OR whom = ?", (name, name))
            for table in ("character_skills", "character_quests"):      # (what their characters got to: theirs too)
                self.db.execute("DELETE FROM %s WHERE (server, name) IN (SELECT server, name FROM characters "
                                "WHERE account = ?)" % table, (name,))
            self.db.execute("DELETE FROM characters WHERE account = ?", (name,))
            if keep_name:
                self.db.execute("UPDATE accounts SET password = '', recover = '', email = '', banned = '', admin = 0, "
                                "google = '', full = '', full_at = 0, pass_until = 0, deleted = ? WHERE name = ?",
                                (time.time(), name))
            else:
                self.db.execute("DELETE FROM accounts WHERE name = ?", (name,))
            self.db.execute("COMMIT")
        except Exception:                       # (anything at all: a transaction left open would stop every write after)
            self.db.execute("ROLLBACK")
            raise

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

    def set_banned(self, name, why):
        self.db.execute("UPDATE accounts SET banned = ? WHERE name = ?", (why, name))

    def count_accounts(self):
        return self.db.execute("SELECT COUNT(*) FROM accounts WHERE deleted = 0").fetchone()[0]

    # ----- owning the game (bought.py checks a purchase with its store before it gets here)
    def owned(self, name):
        """(where the full game was bought: "play", "steam", "itch", "epic", "admin" or "" for not, when, a time pass's
        end)."""
        row = self.db.execute("SELECT full, full_at, pass_until FROM accounts WHERE name = ?", (name,)).fetchone()
        return tuple(row) if row else ("", 0.0, 0.0)

    def set_full(self, name, where):
        """The full game is name's (bought at where), or no longer ("": an admin taking it back)."""
        self.db.execute("UPDATE accounts SET full = ?, full_at = ? WHERE name = ?",
                        (where, time.time() if where else 0, name))

    def claim(self, name, where, ref):
        """A checked purchase (its store's own id for it) for name: "" if it's theirs now (or was already), else the
        account that has it. Only its hash is kept."""
        key = digest(where + ":" + str(ref))
        self.db.execute("INSERT OR IGNORE INTO purchases (ref, name, made) VALUES (?, ?, ?)", (key, name, time.time()))
        row = self.db.execute("SELECT name FROM purchases WHERE ref = ?", (key,)).fetchone()
        return "" if row and row[0].lower() == name.lower() else (row[0] if row else "?")

    def passes_today(self, name):
        """How many time passes name has had in the last day."""
        return self.db.execute("SELECT COUNT(*) FROM passes WHERE name = ? AND made > ?",
                               (name, time.time() - 86400)).fetchone()[0]

    def add_pass(self, name, seconds, most_a_day):
        """A time pass for name: its new end (from now, or from the end of one running), or None if they've had
        most_a_day of them in the last day."""
        now = time.time()
        if self.passes_today(name) >= most_a_day:
            return None
        until = max(now, self.owned(name)[2]) + seconds
        self.db.execute("INSERT INTO passes (name, made) VALUES (?, ?)", (name, now))
        self.db.execute("UPDATE accounts SET pass_until = ? WHERE name = ?", (until, name))
        return until

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
    def new_ticket(self, name, server, relay=False):
        """relay: for a friend's link through here (else for an address, or from the list)."""
        ticket = new_secret()
        self.db.execute("INSERT INTO tickets (ticket, name, server, made, relay) VALUES (?, ?, ?, ?, ?)",
                        (digest(ticket), name, server, time.time(), 1 if relay else 0))
        return ticket

    def use_ticket(self, ticket, server, relayed=None):
        """The player's name if ticket is good for this server (it's used up either way), else None. relayed: whether
        it came to the game through a friend's link here (None: a game from before, that doesn't say)."""
        key = digest(str(ticket))
        row = self.db.execute("SELECT name, server, made, relay FROM tickets WHERE ticket = ?", (key,)).fetchone()
        self.db.execute("DELETE FROM tickets WHERE ticket = ? OR made < ?", (key, time.time() - TICKET_SECONDS))
        if not row or row[1] != server or time.time() - row[2] > TICKET_SECONDS:
            return None
        if relayed is not None and bool(row[3]) != relayed:     # (asked for one way in, and brought by another)
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

    def proves_game(self, key, proof):
        """Is proof this game id's own? The first game to bring one with the id keeps it: a ticket is made out to an id,
        and a game that gave another's can't use it there. (A game from before ids were proved brings none: let be,
        till the id's own game has proved it.)"""
        row = self.db.execute("SELECT proof FROM game_keys WHERE key = ?", (key,)).fetchone()
        if row is None:
            if proof:
                self.db.execute("INSERT INTO game_keys (key, proof, seen) VALUES (?, ?, ?)",
                                (key, digest(proof), time.time()))
            return True
        if not proof or row[0] != digest(proof):
            return False
        self.db.execute("UPDATE game_keys SET seen = ? WHERE key = ?", (time.time(), key))
        return True

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
        names = list(names)
        if not names:
            return {}
        asked = {n.lower(): n for n in names}
        rows = self.db.execute("SELECT p.name, p.server, p.place, p.character, s.url, s.approved FROM playing p LEFT JOIN "
                               "servers s ON s.key = p.server WHERE p.seen > ? AND p.name IN (SELECT value FROM "
                               "json_each(?))", (time.time() - PLAYING_SECONDS, json.dumps(names))).fetchall()
        return {asked[r[0].lower()]: {"server": r[1], "place": r[2], "character": r[3], "url": r[4] if r[5] else ""}
                for r in rows if r[0].lower() in asked}

    # ----- remote servers
    def announce(self, key, secret, name, url, online, most, version, proof=""):
        """A remote server says it's there (key and secret: its own, from the first time; proof: its id's, as tickets
        are checked by). Returns (key, secret)."""
        row = self.db.execute("SELECT secret, name, url FROM servers WHERE key = ?", (key,)).fetchone() if key else None
        if row is None or row[0] != digest(secret or ""):
            # (new: its own id if it has one nobody holds - what tickets are made out to - else one given it)
            fresh = key and row is None and len(key) == 16 and all(ch in "0123456789abcdef" for ch in key) and                 self.proves_game(key, proof)
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
        self.db.execute("DELETE FROM passes WHERE made < ?", (now - 86400,))
        self.db.execute("DELETE FROM game_keys WHERE seen < ?", (now - GAME_KEY_DAYS * 86400,))
        old = now - PROGRESS_DAYS * 86400
        for table in ("character_skills", "character_quests"):
            self.db.execute("DELETE FROM %s WHERE (server, name) IN (SELECT server, name FROM characters WHERE seen < ?)"
                            % table, (old,))
        self.db.execute("DELETE FROM characters WHERE seen < ?", (old,))
        self.db.execute("DELETE FROM reporters WHERE seen < ? AND blocked = 0", (old,))

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

    def count_servers(self):
        """How many are listed just now (what the start screen says): counted, not fetched."""
        return self.db.execute("SELECT COUNT(*) FROM servers WHERE approved = 1 AND seen > ?",
                               (time.time() - SERVER_SECONDS,)).fetchone()[0]

    def server_stats(self):
        """(every server, those approved, those heard from lately)."""
        return self.db.execute("SELECT COUNT(*), COALESCE(SUM(approved), 0), COALESCE(SUM(seen > ?), 0) FROM servers",
                               (time.time() - SERVER_SECONDS,)).fetchone()

    def proves_server(self, key, secret):
        """Is this the secret of a listed server? (A report saying it's that server.)"""
        return bool(self.db.execute("SELECT 1 FROM servers WHERE key = ? AND secret = ? AND approved = 1",
                                    (key, digest(secret or ""))).fetchone())

    def set_approved(self, key, on):
        self.db.execute("UPDATE servers SET approved = ? WHERE key = ?", (1 if on else 0, key))

    def remove_server(self, key):
        self.db.execute("DELETE FROM servers WHERE key = ?", (key,))

    # ----- what every game server says its characters have got to (only as honest as that server: a report's own key
    # is the hash of a secret it keeps, so nobody can write under another's)
    def reporter(self, key):
        row = self.db.execute("SELECT blocked FROM reporters WHERE key = ?", (key,)).fetchone()
        return None if row is None else {"blocked": bool(row[0])}

    def count_reported(self, key):
        return self.db.execute("SELECT COUNT(*) FROM characters WHERE server = ?", (key,)).fetchone()[0]

    def find_total(self, server=""):
        return self.db.execute("SELECT COUNT(*) FROM characters WHERE ? = '' OR server = ?", (server, server)).fetchone()[0]

    def account_standing(self, names):
        """{lower name: is it there, and not deleted?} of the accounts named."""
        rows = self.db.execute("SELECT name, deleted FROM accounts WHERE name IN (SELECT value FROM json_each(?))",
                               (json.dumps(list(names)),)).fetchall()
        return {r[0].lower(): not r[1] for r in rows}

    def take_report(self, key, name, kind, version, listed, characters):
        """One game server's report, in one transaction. characters: [{name, account, level, shards, gold, map, played,
        skills: {skill: (level, xp)}, quests: {quest: (stage, done)}}], each the whole of what that character has: only
        what's changed is written (a quest keeps when it began and when it was finished)."""
        now = time.time()
        self.db.execute("BEGIN")
        try:
            self.db.execute("INSERT INTO reporters (key, name, kind, version, listed, made, seen) VALUES (?, ?, ?, ?, ?, ?, ?) "
                            "ON CONFLICT(key) DO UPDATE SET name = excluded.name, kind = excluded.kind, "
                            "version = excluded.version, listed = excluded.listed, seen = excluded.seen",
                            (key, name, kind, version, 1 if listed else 0, now, now))
            for c in characters:
                self.db.execute("INSERT INTO characters (server, name, account, level, shards, gold, map, played, made, seen) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(server, name) DO UPDATE SET "
                                "account = excluded.account, level = excluded.level, shards = excluded.shards, "
                                "gold = excluded.gold, map = excluded.map, played = excluded.played, seen = excluded.seen",
                                (key, c["name"], c["account"], c["level"], c["shards"], c["gold"], c["map"], c["played"],
                                 now, now))
                self.db.execute("DELETE FROM character_skills WHERE server = ? AND name = ?", (key, c["name"]))
                self.db.executemany("INSERT INTO character_skills (server, name, skill, level, xp) VALUES (?, ?, ?, ?, ?)",
                                    [(key, c["name"], s, lv, xp) for s, (lv, xp) in c["skills"].items()])
                had = {r[0]: r[1:] for r in self.db.execute("SELECT quest, stage, done FROM character_quests WHERE "
                                                            "server = ? AND name = ?", (key, c["name"]))}
                for quest, (stage, done) in c["quests"].items():
                    if had.get(quest) == (stage, done):
                        continue
                    self.db.execute("INSERT INTO character_quests (server, name, quest, stage, done, began, finished) "
                                    "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(server, name, quest) DO UPDATE SET "
                                    "stage = excluded.stage, done = excluded.done, finished = "
                                    "CASE WHEN excluded.done = 0 THEN 0 WHEN finished > 0 THEN finished ELSE ? END",
                                    (key, c["name"], quest, stage, done, now, now if done else 0, now))
                self.db.executemany("DELETE FROM character_quests WHERE server = ? AND name = ? AND quest = ?",
                                    [(key, c["name"], q) for q in had if q not in c["quests"]])
            self.db.execute("COMMIT")
        except Exception:                       # (anything at all: a transaction left open would stop every write after)
            self.db.execute("ROLLBACK")
            raise

    def progress_totals(self):
        """(characters, of those with an account, seen in the last day, in the last week, game servers reporting)."""
        now = time.time()
        return self.db.execute("SELECT COUNT(*), COALESCE(SUM(account != ''), 0), COALESCE(SUM(seen > ?), 0), "
                               "COALESCE(SUM(seen > ?), 0), (SELECT COUNT(*) FROM reporters) FROM characters",
                               (now - 86400, now - 7 * 86400)).fetchone()

    def reporters(self):
        return [{"key": k, "name": n, "kind": kd, "version": v, "listed": bool(li), "blocked": bool(b), "seen": int(s),
                 "characters": c} for k, n, kd, v, li, b, s, c in self.db.execute(
            "SELECT r.key, r.name, r.kind, r.version, r.listed, r.blocked, r.seen, (SELECT COUNT(*) FROM characters c "
            "WHERE c.server = r.key) FROM reporters r ORDER BY r.seen DESC LIMIT 200")]

    def block_reporter(self, key, on):
        """A game server's reports ignored from now on (what it's sent is gone): junk, or its owner asked. Unblocked,
        it's heard again."""
        self.db.execute("BEGIN")
        try:
            for table in ("character_skills", "character_quests", "characters"):
                self.db.execute("DELETE FROM %s WHERE server = ?" % table, (key,))
            self.db.execute("INSERT INTO reporters (key, blocked, made, seen) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT(key) DO UPDATE SET blocked = excluded.blocked",
                            (key, 1 if on else 0, time.time(), time.time()))
            self.db.execute("COMMIT")
        except Exception:                       # (anything at all: a transaction left open would stop every write after)
            self.db.execute("ROLLBACK")
            raise

    def find_characters(self, q="", server="", limit=50, skip=0):
        """The characters found (by their name or their account's), the one played last first, most in a page."""
        found = like(q)
        rows = self.db.execute(
            "SELECT c.server, c.name, c.account, c.level, c.shards, c.gold, c.map, c.seen, r.name, r.kind, r.listed, "
            "(SELECT COUNT(*) FROM character_quests q WHERE q.server = c.server AND q.name = c.name AND q.done = 1) "
            "FROM characters c LEFT JOIN reporters r ON r.key = c.server "
            "WHERE (? = '' OR c.server = ?) AND (? = '' OR c.name LIKE ? ESCAPE '\\' OR c.account LIKE ? ESCAPE '\\') "
            "ORDER BY c.seen DESC LIMIT ? OFFSET ?", (server, server, q, found, found, limit, skip)).fetchall()
        return [{"server": r[0], "name": r[1], "account": r[2], "level": r[3], "shards": r[4], "gold": r[5], "map": r[6],
                 "seen": int(r[7]), "place": r[8] or "", "kind": r[9] or "", "listed": bool(r[10]), "done": r[11]}
                for r in rows]

    def character(self, server, name):
        """One character's skills and quests (the quests by when they began), or None."""
        c = self.db.execute("SELECT c.name, c.account, c.level, c.shards, c.gold, c.map, c.played, c.made, c.seen, r.name, "
                            "r.kind FROM characters c LEFT JOIN reporters r ON r.key = c.server "
                            "WHERE c.server = ? AND c.name = ?", (server, name)).fetchone()
        if c is None:
            return None
        return {"name": c[0], "account": c[1], "level": c[2], "shards": c[3], "gold": c[4], "map": c[5], "played": int(c[6]),
                "made": int(c[7]), "seen": int(c[8]), "place": c[9] or "", "kind": c[10] or "",
                "skills": [{"skill": s, "level": lv, "xp": round(xp, 2)} for s, lv, xp in self.db.execute(
                    "SELECT skill, level, xp FROM character_skills WHERE server = ? AND name = ? ORDER BY level DESC, skill",
                    (server, name))],
                "quests": [{"quest": q, "stage": st, "done": bool(d), "began": int(b), "finished": int(f)}
                           for q, st, d, b, f in self.db.execute(
                    "SELECT quest, stage, done, began, finished FROM character_quests WHERE server = ? AND name = ? "
                    "ORDER BY began", (server, name))]}

    def quest_stats(self, server=""):
        """{quest: (characters that have begun it, those that have finished it)}."""
        return {q: (n, d) for q, n, d in self.db.execute(
            "SELECT quest, COUNT(*), COALESCE(SUM(done), 0) FROM character_quests WHERE ? = '' OR server = ? GROUP BY quest",
            (server, server))}

    def quest_stages(self, quest, server=""):
        """[(stage, how many are at it)]: where those on a quest have got to."""
        return self.db.execute("SELECT stage, COUNT(*) FROM character_quests WHERE quest = ? AND (? = '' OR server = ?) "
                               "GROUP BY stage ORDER BY stage", (quest, server, server)).fetchall()

    def skill_stats(self, server=""):
        """[{skill, characters, average, highest, and how many have reached each of levels 5, 10, 15, 20, 25}]."""
        rows = self.db.execute(
            "SELECT skill, COUNT(*), AVG(level), MAX(level), COALESCE(SUM(level >= 5), 0), COALESCE(SUM(level >= 10), 0), "
            "COALESCE(SUM(level >= 15), 0), COALESCE(SUM(level >= 20), 0), COALESCE(SUM(level >= 25), 0) "
            "FROM character_skills WHERE ? = '' OR server = ? GROUP BY skill ORDER BY AVG(level) DESC",
            (server, server)).fetchall()
        return [{"skill": r[0], "characters": r[1], "average": round(r[2], 1), "highest": r[3], "reached": list(r[4:])}
                for r in rows]
