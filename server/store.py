"""Everything the server keeps: accounts, characters and the shared world, in one SQLite database (server-data/ashen.db
by default; DS_DB to put it elsewhere). Characters and the world are JSON. A row of accounts is a character: its name
(one of a kind on this server), whose it is (owner: "a:<Shards account>" or "d:<a device's key, hashed>"; empty for
an old one with a password of its own, till it's brought in) and the Admin button."""
import json
import logging
import os
import shutil
import sqlite3
import time

log = logging.getLogger("ashen.store")

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    pw_hash TEXT NOT NULL DEFAULT '',
    admin INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS characters (
    name TEXT PRIMARY KEY COLLATE NOCASE,
    state TEXT NOT NULL,
    updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    hash TEXT PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    created REAL NOT NULL,
    used REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS world (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated REAL NOT NULL
);
"""

# (columns added since: put on an older database as it opens)
COLUMNS = [("accounts", "owner", "TEXT NOT NULL DEFAULT ''")]


OLD_NAME = "dragonsword.db"   # (the database's name before the game was Shards of Ashen everywhere)


def moved_from_old_name(path):
    """A new database's name with no file yet, beside one under the old name: the old one (and its -wal and -shm,
    which hold what it last wrote) moved over, so the world, accounts and characters carry on."""
    folder = os.path.dirname(os.path.abspath(path))
    old = os.path.join(folder, OLD_NAME)
    if os.path.exists(path) or os.path.basename(path) == OLD_NAME or not os.path.exists(old):
        return False
    for tail in ("", "-wal", "-shm"):
        if os.path.exists(old + tail):
            os.replace(old + tail, path + tail)
    log.info("The database is %s now (it was %s)", os.path.basename(path), OLD_NAME)
    return True


class Store:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        moved_from_old_name(path)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        for table, col, kind in COLUMNS:
            if col not in [r[1] for r in self.db.execute("PRAGMA table_info(%s)" % table)]:
                self.db.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, kind))
        self.forget_tokens()

    def close(self):
        self.db.close()

    # ----- accounts
    def account(self, name):
        """(name as stored, pw_hash, admin) or None."""
        row = self.db.execute("SELECT name, pw_hash, admin FROM accounts WHERE name = ?", (name,)).fetchone()
        return row

    def create_account(self, name, pw_hash, admin=False, owner=""):
        self.db.execute("INSERT INTO accounts (name, pw_hash, admin, created, owner) VALUES (?, ?, ?, ?, ?)",
                        (name, pw_hash, 1 if admin else 0, time.time(), owner))

    def owner(self, name):
        row = self.db.execute("SELECT owner FROM accounts WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None

    def set_owner(self, name, owner):
        """name is owner's now (and needs no password: it's dropped)."""
        self.db.execute("UPDATE accounts SET owner = ?, pw_hash = '' WHERE name = ?", (owner, name))

    def characters_of(self, owner):
        """owner's characters here, the one played last first."""
        return [r[0] for r in self.db.execute(
            "SELECT a.name FROM accounts a LEFT JOIN characters c ON c.name = a.name WHERE lower(a.owner) = lower(?) "
            "ORDER BY COALESCE(c.updated, a.created) DESC", (owner,))] if owner else []

    def owners_from_old_links(self):
        """Characters the central server's tickets made (or linked) before characters had owners: their account's
        (a character made by a ticket was named for its account)."""
        for (key,) in self.db.execute("SELECT key FROM world WHERE key LIKE 'set:central:%'").fetchall():
            row = self.account(key[len("set:central:"):])
            if row is not None and not self.owner(row[0]):
                self.set_owner(row[0], "a:" + row[0])
            self.db.execute("DELETE FROM world WHERE key = ?", (key,))

    def old_ones(self):
        """How many old characters (a password of their own, nobody's yet) wait to be brought in."""
        return self.db.execute("SELECT COUNT(*) FROM accounts WHERE owner = '' AND pw_hash != ''").fetchone()[0]

    def set_password(self, name, pw_hash):
        cur = self.db.execute("UPDATE accounts SET pw_hash = ? WHERE name = ?", (pw_hash, name))
        self.forget_tokens(name)
        return cur.rowcount > 0

    def set_admin(self, name, admin):
        self.db.execute("UPDATE accounts SET admin = ? WHERE name = ?", (1 if admin else 0, name))

    # ----- (logging in without a password is gone: what's left of its tokens is cleared on start and on a new
    # password, so none of them can ever be used again)
    def forget_tokens(self, name=None):
        if name is None:
            self.db.execute("DELETE FROM tokens")
        else:
            self.db.execute("DELETE FROM tokens WHERE name = ?", (name,))

    def accounts(self):
        return self.db.execute("SELECT name, pw_hash != '', admin, owner FROM accounts ORDER BY name").fetchall()

    # ----- characters
    def load_character(self, name):
        row = self.db.execute("SELECT state FROM characters WHERE name = ?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_character(self, name, state):
        self.db.execute("INSERT INTO characters (name, state, updated) VALUES (?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET state = excluded.state, updated = excluded.updated",
                        (name, json.dumps(state, separators=(",", ":")), time.time()))

    def save_characters(self, items, world=None):
        """[(name, state)] in one transaction, and the world's state with them if it's given."""
        self.db.execute("BEGIN")
        try:
            for name, state in items:
                self.save_character(name, state)
            if world is not None:
                self.save_world(world)
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    # ----- the world
    def load_world(self):
        row = self.db.execute("SELECT value FROM world WHERE key = 'state'").fetchone()
        return json.loads(row[0]) if row else None

    def save_world(self, state):
        self.db.execute("INSERT INTO world (key, value, updated) VALUES ('state', ?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated = excluded.updated",
                        (json.dumps(state, separators=(",", ":")), time.time()))

    def setting(self, key, default=""):
        """A server-wide setting kept with the world (the world table, key 'set:<key>')."""
        row = self.db.execute("SELECT value FROM world WHERE key = ?", ("set:" + key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.db.execute("INSERT INTO world (key, value, updated) VALUES (?, ?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated = excluded.updated",
                        ("set:" + key, str(value), time.time()))
        self.db.commit()

    def drop_setting(self, key):
        self.db.execute("DELETE FROM world WHERE key = ?", ("set:" + key,))
        self.db.commit()

    # ----- backups
    def backup(self, folder, keep=14):
        """A copy of the database in folder (ashen-YYYYMMDD-HHMM.db), keeping the newest keep."""
        os.makedirs(folder, exist_ok=True)
        out = os.path.join(folder, time.strftime("ashen-%Y%m%d-%H%M.db"))
        dest = sqlite3.connect(out)
        with dest:
            self.db.backup(dest)
        dest.close()
        files = sorted(f for f in os.listdir(folder) if f.startswith(("ashen-", "dragonsword-")) and f.endswith(".db"))
        for f in files[:-keep]:
            try:
                os.remove(os.path.join(folder, f))
            except OSError:
                pass
        return out
