"""The Isle's creatures a level or two lower (dev/Roadmap-8.md, group 3): it's where you learn to fight. Every
creature placed on the Isle's maps (Config.ini [Demo] Area: the Isle and its caves), or by a map's own script there
(the hobgoblins' lair: Add.Entity), that isn't a friend gets `Level=` on its line: its kind's level, one lower (two
from level 4 up), never under 1, and the same each time it comes back (no little above or below, as one of many has
elsewhere: world.py set_npc_level). A pass over the built maps (the owner's hand is on them): it only adds the option,
and a line that has a Level= already keeps it. Safe to run again.

  python -I "dev\\migrate\\isle_levels.py"
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsedit.project import read_text_lines, write_text_lines  # noqa: E402
from common import Ini, p  # noqa: E402


def isle_area():
    """Config.ini [Demo] Area: [((x, y, z), (x, y, z))]."""
    area = Ini(p("data", "Config.ini")).get("Demo", "Area") or ""
    out = []
    for part in area.split(";"):
        ends = part.split()
        if len(ends) == 2:
            a, b = (tuple(int(v) for v in e.split(",")) for e in ends)
            out.append((tuple(map(min, a, b)), tuple(map(max, a, b))))
    return out


def lower(level):
    return max(1, level - (2 if level >= 4 else 1))


def placed(parts, script):
    """(its kind, where its options are) for a creature's line, or None: a map's `NPC kind x y options`, a script's
    `NN Add.Entity x,y kind NPC options`."""
    if script:
        return (parts[3], 5) if len(parts) >= 5 and parts[1] == "Add.Entity" and parts[4] == "NPC" else None
    return (parts[1], 4) if parts[0] == "NPC" and len(parts) >= 4 else None


def main():
    ents = Ini(p("data", "Entities.ini"))
    area = isle_area()
    n, files = 0, 0
    for path in sorted(glob.glob(os.path.join(ROOT, "maps", "*.txt"))):
        name = os.path.basename(path)
        try:
            at = tuple(int(v) for v in name[:-4].split(","))
        except ValueError:
            continue
        if len(at) != 3 or not any(all(lo[i] <= at[i] <= hi[i] for i in range(3)) for lo, hi in area):
            continue
        for path, script in ((path, False), (os.path.join(ROOT, "data", "Scripts", name), True)):
            if not os.path.exists(path):
                continue
            out = []
            for line in read_text_lines(path):
                parts = line.split("\t")
                found = placed(parts, script)
                if found:
                    kind, o = found
                    opts = parts[o] if len(parts) > o else ""
                    words = {w.split("=", 1)[0].upper(): w.split("=", 1)[-1] for w in opts.split()}
                    attitude = words.get("ATTITUDE") or ents.get(kind, "Attitude") or ""
                    base = int(float(ents.get(kind, "Level") or 0))
                    if base and "LEVEL" not in words and attitude.strip().upper() != "GOOD":
                        opts = (("" if opts == "-" else opts) + " Level=%d" % lower(base)).strip()
                        line = "\t".join(parts[:o] + [opts] + parts[o + 1:])
                        n += 1
                out.append(line)
            if write_text_lines(path, out):
                files += 1
    print("%d creatures given a level, in %d of the Isle's maps and scripts" % (n, files))


if __name__ == "__main__":
    main()
