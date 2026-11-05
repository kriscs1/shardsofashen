"""Looking after the server's accounts (run it where the database is; stop the server first or not, either is safe):

  python tools/admin.py list                        the characters, whose they are, the admins
  python tools/admin.py owner <name> <account>      give a character to a Hallisium account (no password: it's theirs)
  python tools/admin.py admin <name> on|off        the Admin button (give items, set skills, god mode)
  python tools/admin.py backup                     a copy of the database in server-data/backups

--db <path> (or DS_DB) for a database somewhere else."""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from server import auth  # noqa: E402
from server.store import Store  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Shards of Ashen server accounts")
    p.add_argument("--db", default=os.environ.get("DS_DB", os.path.join(ROOT, "server-data", "ashen.db")))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    ow = sub.add_parser("owner")
    ow.add_argument("name")
    ow.add_argument("account")
    ad = sub.add_parser("admin")
    ad.add_argument("name")
    ad.add_argument("state", choices=("on", "off"))
    sub.add_parser("backup")
    args = p.parse_args()
    store = Store(args.db)
    if args.cmd == "list":
        rows = store.accounts()
        if not rows:
            print("No accounts yet.")
        for name, _, admin, owner in rows:
            whose = ("account " + owner[2:]) if owner.startswith("a:") else "a device's" if owner else "nobody's"
            print("%-20s %s%s" % (name, whose, "  (admin)" if admin else ""))
    elif args.cmd == "owner":
        row = store.account(args.name)
        account = auth.clean_name(args.account)
        if row is None or not account:
            sys.exit("No character called %s." % args.name if row is None else "That isn't an account's name.")
        store.set_owner(row[0], "a:" + account)
        print("%s is %s's now." % (row[0], account))
    elif args.cmd == "admin":
        if store.account(args.name) is None:
            sys.exit("No account called %s." % args.name)
        store.set_admin(args.name, args.state == "on")
        print("%s: admin %s." % (args.name, args.state))
    elif args.cmd == "backup":
        print(store.backup(os.path.join(os.path.dirname(os.path.abspath(args.db)), "backups")))
    store.close()


if __name__ == "__main__":
    main()
