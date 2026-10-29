"""Rugs go under the decor (Layer=Under): a chair, a table, a pew can stand on one. Run it once (again: nothing to do).

  python -I "dev\\migrate\\rugs_under.py"

  * Tiles.ini: every Rug tile gets Layer=Under (it was Layer=Decor).
  * Maps (all of them, sub-folders too): a cell's +Decor(RugNNN) becomes +Under(RugNNN), so its decor slot is free.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ashen import ini  # noqa: E402

TILES_INI = os.path.join(ROOT, "data", "Tiles.ini")


def main():
    rugs = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "sprites", "Tiles", "Rug*.png")))
    n = 0
    for r in rugs:
        if ini.section(r, TILES_INI) and ini.read(r, "Layer", "", TILES_INI).strip().lower() != "under":
            ini.write(r, "Layer", "Under", TILES_INI)
            n += 1
    names = "|".join(re.escape(r) for r in rugs)
    pat = re.compile(r"\+Decor\((%s)\)" % names)
    maps = 0
    for path in glob.glob(os.path.join(ROOT, "maps", "**", "*.txt"), recursive=True):
        raw = open(path, "rb").read().decode("cp1252")
        new = pat.sub(lambda m: "+Under(%s)" % m.group(1), raw)
        if new != raw:
            open(path, "wb").write(new.encode("cp1252"))
            maps += 1
    print("Rugs: %d tiles are Layer=Under now; %d maps' rugs moved under their decor" % (n, maps))


if __name__ == "__main__":
    main()
