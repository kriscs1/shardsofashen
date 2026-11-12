"""Everything the server keeps: accounts, characters and the shared world, in one SQLite database (server-data/ashen.db
by default; DS_DB to put it elsewhere). Characters and the world are JSON. A row of accounts is a character: its name
(one of a kind on this server), whose it is (owner: "a:<Hallisium account>" or "d:<a device's key, hashed>") and the
Admin button. (pw_hash: a column from when characters had passwords, always empty now.)"""
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
        self.written = {}               # (name -> the state last written: one that hasn't changed isn't written again)
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
        """name is owner's now."""
        self.db.execute("UPDATE accounts SET owner = ?, pw_hash = '' WHERE name = ?", (owner, name))

    def characters_of(self, owner):
        """owner's characters here, the one played last first."""
        return [r[0] for r in self.db.execute(
            "SELECT a.name FROM accounts a LEFT JOIN characters c ON c.name = a.name WHERE lower(a.owner) = lower(?) "
            "ORDER BY COALESCE(c.updated, a.created) DESC", (owner,))] if owner else []

    def set_admin(self, name, admin):
        self.db.execute("UPDATE accounts SET admin = ? WHERE name = ?", (1 if admin else 0, name))

    # ----- (the tokens of logging in long ago: cleared on start, so none of them can ever be used again)
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

    def save_character(self, name, state, text=None):
        text = text if text is not None else json.dumps(state, separators=(",", ":"))
        self.db.execute("INSERT INTO characters (name, state, updated) VALUES (?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET state = excluded.state, updated = excluded.updated",
                        (name, text, time.time()))
        self.written.pop(name, None)

    def characters_since(self, mark, limit):
        """[(name, state, when, owner)] of those saved at or since mark (a clock can read the same for two saves: the last
        one told comes again, and is seen to be nothing new), the earliest first: for server/progress.py."""
        return self.db.execute("SELECT c.name, c.state, c.updated, COALESCE(a.owner, '') FROM characters c LEFT JOIN "
                               "accounts a ON a.name = c.name WHERE c.updated >= ? ORDER BY c.updated LIMIT ?",
                               (mark, limit)).fetchall()

    def save_characters(self, items, world=None):
        """[(name, state)] in one transaction, and the world's state with them if it's given."""
        done = {}
        self.db.execute("BEGIN")
        try:
            for name, state in items:
                text = json.dumps(state, separators=(",", ":"))
                if self.written.get(name) != text:      # (the same as last time: nothing to write)
                    self.save_character(name, state, text)
                    done[name] = text
            if world is not None:
                self.save_world(world)
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        self.written.update(done)                       # (only once it's in: a save that failed is tried again whole)

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
