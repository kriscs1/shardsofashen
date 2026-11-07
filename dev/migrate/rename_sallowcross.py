"""The hamlet in the Sallow Waste is Sallowcross (it was Moorcross: a moor's name in a dusty waste), the open land round
it the Greyflats (it was Greymoor), and its shepherd's quest Wolves of the Greyflats (it was Wolves of the Moor). Every
place Id, thing's Id, script, quest, label, shardstone and word that said them says the new ones now, and the zone's
own key (Dustlands, which made Ids like Zone_Dustlands) is Sallow_Waste.
Characters saved before keep what they had: an attribute named for the old names (Waystone.Moorcross, Secret_Moorcross,
Zone_Chest_Dustlands) is read under its new name as they load (dsengine/renames.py RENAMED_WORDS), and a quest's notes
under its new name (RENAMED_QUESTS).
It refuses to run again (nothing says Moorcross any more).
Usage: python -I dev/migrate/rename_sallowcross.py"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p  # noqa: E402

KEEP = {"rename_ashen.py", "rename_shards_of_ashen.py", "rename_northport.py", "rename_sallowcross.py", "renames.py",
        "Roadmap.md", "Roadmap-4.md", "Roadmap-5.md"}         # (what renamed things before, and the to-do lists: history)

SWAPS = [                                                   # (the most particular first)
    (b"Wolves of the Moor", b"Wolves of the Greyflats"), (b"wolves of the moor", b"wolves of the greyflats"),
    (b"Thin out the moor wolves", b"Thin out the Greyflats' wolves"),
    (b"on the eastern moor", b"out east on the flats"),
    (b"They prowl the whole moor.", b"They prowl the whole of the flats."),
    (b"out on the open moor", b"out on the open flats"),
    (b"the wolves on the moor", b"the wolves on the Greyflats"),
    (b"The leader of the moor pack", b"The leader of the Greyflats pack"),
    (b"Greymoor=", b"The Greyflats="), (b'"Greymoor":', b'"The Greyflats":'),
    (b"Greymoor", b"the Greyflats"), (b"greymoor", b"the greyflats"),
    (b"Moorcross", b"Sallowcross"), (b"MOORCROSS", b"SALLOWCROSS"), (b"moorcross", b"sallowcross"),
    (b"Zone_Chest_Dustlands", b"Zone_Chest_Sallow_Waste"), (b"Zone_Dustlands", b"Zone_Sallow_Waste"),
    (b'"Dustlands"', b'"Sallow_Waste"'),                     # (the zone's key in the builders)
]


def swap(b):
    for old, new in SWAPS:
        b = b.replace(old, new)
    return b.replace(b". the Greyflats", b". The Greyflats").replace(b"\\the Greyflats", b"\\The Greyflats")


def files():
    for top, exts in (("data", (".ini", ".txt")), ("maps", (".txt",)), ("tests", (".py",)),
                      (os.path.join("dev", "migrate"), (".py", ".txt", ".json")), ("dev", (".md", ".txt")),
                      ("web", (".js", ".html", ".css")), ("dsengine", (".py",)), ("server", (".py",)),
                      ("dsedit", (".py",))):
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
    yield p("CLAUDE.md")


def main():
    print("Superseded: the hamlet is Greyford now (rename_greyford.py).")
    return
    hit = [f for f in files() if swap(open(f, "rb").read()) != open(f, "rb").read()]
    if not any(b"Moorcross" in open(f, "rb").read() for f in hit):
        print("Nothing says Moorcross: done already.")
        return
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
    print("Sallowcross: %d files changed, %d scripts renamed" % (len(hit), moved))


if __name__ == "__main__":
    main()
