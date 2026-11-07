"""The hamlet on the Greyflats is Greyford (it was Sallowcross, and before that Moorcross: the owner's choice, by the Dry
Ford). Every place Id, thing's Id, script, label, shardstone and word that said Sallowcross says Greyford now; the
Sallow Waste round it keeps its name.
Characters saved before keep what they had: an attribute named for either old name (Waystone.Moorcross,
Waystone.Sallowcross, Secret_Sallowcross) is read under the new one as they load (dsengine/renames.py RENAMED_WORDS).
It refuses to run again (nothing in the data or the maps says Sallowcross any more).
Usage: python -I dev/migrate/rename_greyford.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rename_sallowcross as R  # noqa: E402  (the same files and the same way of moving scripts)

R.KEEP.add("rename_greyford.py")

SWAPS = [(b"Sallowcross", b"Greyford"), (b"SALLOWCROSS", b"GREYFORD"), (b"sallowcross", b"greyford")]


def swap(b):
    for old, new in SWAPS:
        b = b.replace(old, new)
    return b


def main():
    hit = [f for f in R.files() if swap(open(f, "rb").read()) != open(f, "rb").read()]
    if not any(b"Sallowcross" in open(f, "rb").read() for f in hit
               if os.path.relpath(f, R.p()).split(os.sep)[0] in ("data", "maps")):
        print("Nothing says Sallowcross: done already.")
        return
    for f in hit:
        b = open(f, "rb").read()
        open(f, "wb").write(swap(b))
    R.swap = swap                                       # (the scripts named for it: moved by the same code)
    moved = 0
    folder = R.p("data", "Scripts")
    for f in sorted(os.listdir(folder)):
        new = swap(f.encode("cp1252")).decode("cp1252")
        if new != f:
            src, dst = os.path.join(folder, f), os.path.join(folder, new)
            if os.path.exists(dst):
                os.remove(src)
            elif R.subprocess.run(["git", "mv", src, dst], cwd=R.p(), capture_output=True).returncode:
                os.rename(src, dst)
            moved += 1
    print("Greyford: %d files changed, %d scripts renamed" % (len(hit), moved))


if __name__ == "__main__":
    main()
