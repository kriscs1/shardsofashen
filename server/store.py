"""Everything the server keeps: accounts, characters and the shared world, in one SQLite database (server-data/dragonsword.db
by default; DS_DB to put it elsewhere). Characters and the world are JSON."""
import json
import os
import shutil
import sqlite3
import time

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


class Store:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.forget_tokens()

    def close(self):
        self.db.close()

    # ----- accounts
    def account(self, name):
        """(name as stored, pw_hash, admin) or None."""
        row = self.db.execute("SELECT name, pw_hash, admin FROM accounts WHERE name = ?", (name,)).fetchone()
        return row

    def create_account(self, name, pw_hash, admin=False):
        self.db.execute("INSERT INTO accounts (name, pw_hash, admin, created) VALUES (?, ?, ?, ?)",
                        (name, pw_hash, 1 if admin else 0, time.time()))

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
        return self.db.execute("SELECT name, pw_hash != '', admin FROM accounts ORDER BY name").fetchall()

    # ----- characters
    def load_character(self, name):
        row = self.db.execute("SELECT state FROM characters WHERE name = ?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_character(self, name, state):
        self.db.execute("INSERT INTO characters (name, state, updated) VALUES (?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET state = excluded.state, updated = excluded.updated",
                        (name, json.dumps(state, separators=(",", ":")), time.time()))

    def save_characters(self, items):
        """[(name, state)] in one transaction."""
        self.db.execute("BEGIN")
        try:
            for name, state in items:
                self.save_character(name, state)
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

    # ----- backups
    def backup(self, folder, keep=14):
        """A copy of the database in folder (dragonsword-YYYYMMDD-HHMM.db), keeping the newest keep."""
        os.makedirs(folder, exist_ok=True)
        out = os.path.join(folder, time.strftime("dragonsword-%Y%m%d-%H%M.db"))
        dest = sqlite3.connect(out)
        with dest:
            self.db.backup(dest)
        dest.close()
        files = sorted(f for f in os.listdir(folder) if f.startswith("dragonsword-") and f.endswith(".db"))
        for f in files[:-keep]:
            try:
                os.remove(os.path.join(folder, f))
            except OSError:
                pass
        return out
