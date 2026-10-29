"""The port city is Northport (it was Southport, then Northgate on its signs while its Ids stayed Southport): every place
Id, thing's Id, script, quest marker, label, shardstone and word that said Southport or Northgate says Northport now. And
Northport's landing and its port were two places a few steps apart: they're one, Northport_Port (the ferry's pier,
Northport_Pier, is its own).
Characters saved before keep what they had: an attribute named for Southport (Waystone.Southport, the shardstone they
activated) is read under its new name as they load (dsengine/renames.py RENAMED_WORDS).
It refuses to run again (nothing says Southport any more).
Usage: python -I dev/migrate/rename_northport.py"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p  # noqa: E402

KEEP = {"rename_ashen.py", "rename_shards_of_ashen.py", "rename_northport.py", "renames.py"}   # (what renamed it before: history)


def swap(b):
    b = b.replace(b"Southport_Landing", b"Northport_Port")       # (the landing and the port: one place)
    b = b.replace(b"Southport", b"Northport").replace(b"Northgate", b"Northport")
    return b.replace(b"SOUTHPORT", b"NORTHPORT").replace(b"NORTHGATE", b"NORTHPORT")


def files():
    for top, exts in (("data", (".ini", ".txt")), ("maps", (".txt",)), ("tests", (".py",)), ("saves", (".ini",)),
                      (os.path.join("dev", "migrate"), (".py", ".txt", ".json")), ("dev", (".md", ".txt")),
                      ("web", (".js", ".html", ".css")), ("dsengine", (".py",)), ("server", (".py",))):
        root = p(top)
        if not os.path.isdir(root):
            continue
        for d, subs, fs in os.walk(root):
            subs[:] = [s for s in subs if s not in ("__pycache__", "Archive", "assets", "Renders")]
            if top == "dev" and d != root:
                continue                                    # (dev itself only: dev\migrate is its own)
            for f in fs:
                if f.endswith(exts) and f not in KEEP:
                    yield os.path.join(d, f)


def main():
    hit = [f for f in files() if b"Southport" in open(f, "rb").read() or b"Northgate" in open(f, "rb").read()]
    if not hit:
        print("Nothing says Southport or Northgate: done already.")
        return
    lm = p("maps", "4,4,0.txt")                            # (the landing's own Id line goes: the port's stays)
    b = open(lm, "rb").read()
    open(lm, "wb").write(re.sub(rb"Id\tSouthport_Landing\t[^\r\n]*\r?\n", b"", b))
    for f in hit:
        b = open(f, "rb").read()
        open(f, "wb").write(swap(b))
    moved = 0
    folder = p("data", "Scripts")
    for f in sorted(os.listdir(folder)):
        new = swap(f.encode("cp1252")).decode("cp1252")
        if new != f:
            src, dst = os.path.join(folder, f), os.path.join(folder, new)
            if os.path.exists(dst):                       # (both: the old one is the one let go)
                os.remove(src)
            elif subprocess.run(["git", "mv", src, dst], cwd=p(), capture_output=True).returncode:
                os.rename(src, dst)
            moved += 1
    print("Northport: %d files changed, %d scripts renamed" % (len(hit), moved))


if __name__ == "__main__":
    main()
