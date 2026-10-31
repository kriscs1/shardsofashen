"""Prey is Passive: every NPC placed on a map whose kind flees (Entities.ini Flees=1: rabbits, ducks, frogs, seals,
otters, hens, cows, sheep) gets Attitude=Passive on its map line - it can be hunted, never attacks first, runs when
hit - where the builders had written Attitude=Bad (a foe: it kept you from sleeping) or Good (it couldn't be hunted).
The builders write Passive for them now too (estforlan/life.py PREY, build_water_animals.py, build_isle.py,
build_isle_east.py). Safe to run again.

  python -I "dev\\migrate\\prey_passive.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ashen import ini  # noqa: E402
from dsedit.project import read_text_lines, write_text_lines  # noqa: E402

ENTITIES = os.path.join(ROOT, "data", "Entities.ini")
H = 21


def prey():
    return {s for s, _ in ini.sections(ENTITIES) if s and (ini.read(s, "Flees", "", ENTITIES) or "").strip() == "1"}


def main():
    kinds = prey()
    paths = [os.path.join(ROOT, "maps", f) for f in sorted(os.listdir(os.path.join(ROOT, "maps"))) if f.endswith(".txt")]
    paths.append(os.path.join(ROOT, "data", "Homestead.txt"))
    n, maps = 0, 0
    for path in paths:
        if not os.path.exists(path):
            continue
        lines = read_text_lines(path)
        out = list(lines)
        for i in range(H, len(lines)):
            f = lines[i].split("\t")
            if f[0] != "NPC" or len(f) < 4 or f[1] not in kinds:
                continue
            while len(f) < 5:
                f.append("")
            words = [w for w in f[4].split() if not w.lower().startswith("attitude=")]
            new = " ".join(["Attitude=Passive"] + words)
            if new != f[4]:
                f[4] = new
                out[i] = "\t".join(f)
                n += 1
        if out != lines:
            write_text_lines(path, out)
            maps += 1
    print("prey made Passive: %d on %d maps (%s)" % (n, maps, ", ".join(sorted(kinds))))


if __name__ == "__main__":
    main()
