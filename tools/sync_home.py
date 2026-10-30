"""Copies the start screen (web/home/: the same in every version) into the Android app's assets. Run it after editing
web/home/; tests/test_central.py fails while the two differ. The desktop app reads web/home/ itself, and a browser
gets it from the central server.

  python -I tools/sync_home.py
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web", "home")
DEST = os.path.join(ROOT, "android", "app", "src", "main", "assets", "home")
FILES = ("index.html", "config.js")


def main():
    os.makedirs(DEST, exist_ok=True)
    n = 0
    for f in FILES:
        a, b = os.path.join(SRC, f), os.path.join(DEST, f)
        if not os.path.exists(b) or open(a, "rb").read() != open(b, "rb").read():
            shutil.copyfile(a, b)
            n += 1
    print("The start screen: %d file%s copied into the Android app" % (n, "" if n == 1 else "s"))


if __name__ == "__main__":
    main()
