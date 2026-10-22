"""Looking after the server's accounts (run it where the database is; stop the server first or not, either is safe):

  python tools/admin.py list
  python tools/admin.py password <name>            set a password (asks for it) - also makes the account if needed
  python tools/admin.py admin <name> on|off        the Admin button (give items, set skills, god mode)
  python tools/admin.py backup                     a copy of the database in data/backups

--db <path> (or DS_DB) for a database somewhere else."""
import argparse
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from server import auth  # noqa: E402
from server.store import Store  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Dragon Sword server accounts")
    p.add_argument("--db", default=os.environ.get("DS_DB", os.path.join(ROOT, "data", "dragonsword.db")))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    pw = sub.add_parser("password")
    pw.add_argument("name")
    pw.add_argument("--password", help="(else it is asked for)")
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
        for name, has_pw, admin in rows:
            print("%-20s %s%s" % (name, "password set" if has_pw else "NO PASSWORD", "  (admin)" if admin else ""))
    elif args.cmd == "password":
        name = auth.clean_name(args.name)
        if not name:
            sys.exit("That isn't a valid name.")
        password = args.password or getpass.getpass("New password for %s: " % name)
        if len(password) < 4:
            sys.exit("Use at least 4 characters.")
        if store.account(name) is None:
            store.create_account(name, auth.hash_password(password))
            print("Made the account %s." % name)
        else:
            store.set_password(name, auth.hash_password(password))
            print("Password set for %s." % name)
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
