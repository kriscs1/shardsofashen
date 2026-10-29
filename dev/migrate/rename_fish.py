"""The fish from the sea's ripples is a herring now (it was just "Raw Fish"): Raw_Herring, Cooked_Herring and
Burnt_Herring, as the trout, salmon, swordfish and cave eel are all their own fish, raw, cooked and burnt. Every name in
the data, the maps, the scripts (and their file names), the builders and the pictures; what a message or a description
calls it, too. Characters and the world saved with the old names are put right as they load (dsengine/renames.py).
It refuses to run again (no Raw_Fish left).
Usage: python -I dev/migrate/rename_fish.py"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p  # noqa: E402

NAMES = {"Raw_Fish": "Raw_Herring", "Cooked_Fish": "Cooked_Herring", "Burnt_Fish": "Burnt_Herring"}
WORDS = {"Raw Fish": "Raw Herring", "raw fish": "raw herring", "Cooked Fish": "Cooked Herring",
         "cooked fish": "cooked herring", "Burnt Fish": "Burnt Herring", "burnt fish": "burnt herring",
         "A fresh fish. Cook it on a fire.": "A fresh herring, silver from the sea. Cook it on a fire.",
         "Nicely cooked fish.": "A herring, nicely cooked."}
KEEP = {"rename_fish.py", "rename_items.py", "renames.py"}


def swap(t):
    for a, b in NAMES.items():
        t = t.replace(a.encode(), b.encode())
    for a, b in WORDS.items():
        t = t.replace(a.encode(), b.encode())
    return t


def files():
    for top, exts in (("data", (".ini", ".txt")), ("maps", (".txt",)), ("tests", (".py",)), ("saves", (".ini",)),
                      (os.path.join("dev", "migrate"), (".py",)), ("web", (".js",)), ("dsengine", (".py",))):
        for d, subs, fs in os.walk(p(top)):
            subs[:] = [s for s in subs if s not in ("__pycache__", "Archive", "assets")]
            for f in fs:
                if f.endswith(exts) and f not in KEEP:
                    yield os.path.join(d, f)


def mv(src, dst):
    if subprocess.run(["git", "mv", src, dst], cwd=p(), capture_output=True).returncode:
        os.rename(src, dst)


def main():
    hit = [f for f in files() if any(a.encode() in open(f, "rb").read() for a in NAMES)]
    if not hit:
        print("No Raw_Fish anywhere: done already.")
        return
    for f in hit:
        new = swap(open(f, "rb").read())              # (read first: opening to write empties it)
        open(f, "wb").write(new)
    n = 0
    for folder in (p("data", "Scripts"), p("sprites", "Entities")):
        for f in sorted(os.listdir(folder)):
            new = swap(f.encode("cp1252")).decode("cp1252")
            if new != f:
                mv(os.path.join(folder, f), os.path.join(folder, new))
                n += 1
    print("Herring: %d files changed, %d scripts and pictures renamed" % (len(hit), n))


if __name__ == "__main__":
    main()
