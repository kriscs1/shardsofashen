"""Townsfolk take the stairs: the house stairs (Stairs001 up, Stairs002 down) get Stairs=1 in Tiles.ini, so an NPC
whose bed is upstairs (Bed=x,y Bed.Level=1) or whose home is on another level (Home.Level=) walks to them and up or
down (npcs.py npc_to_level). Edwin and Maren are one each now, not a day self downstairs and a night self upstairs:
by day at her counter and his desk, at night up the stairs to their double bed (2,1,1). build_heir_isle.py writes
them so too. Safe to run again.

  python -I "dev\\migrate\\npc_stairs.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from ashen import ini  # noqa: E402
from dsedit.project import read_text_lines, write_text_lines  # noqa: E402

TILES = os.path.join(ROOT, "data", "Tiles.ini")
STAIRS = ("Stairs001", "Stairs002")
H = 21
BEDS = {"Maren_At_Counter": "Bed=13,1 Bed.Level=1",          # (the double bed's left half, and its right)
        "Edwin_At_Desk": "Bed=14,1 Bed.Level=1"}


def stairs():
    n = 0
    for name in STAIRS:
        if (ini.read(name, "Stairs", "", TILES) or "").strip() != "1":
            ini.write(name, "Stairs", "1", TILES)
            n += 1
    print("stairs townsfolk take: %d marked (%s)" % (n, ", ".join(STAIRS)))


def edwin_and_maren():
    down, up = os.path.join(ROOT, "maps", "2,1,0.txt"), os.path.join(ROOT, "maps", "2,1,1.txt")
    lines = read_text_lines(down)
    out = list(lines)
    for i in range(H, len(lines)):
        f = lines[i].split("\t")
        if f[0] != "NPC" or len(f) < 5:
            continue
        words = f[4].split()
        nid = next((w[3:] for w in words if w.startswith("Id=")), "")
        if nid not in BEDS:
            continue
        words = [w for w in words if not w.split("=")[0] in ("Schedule", "Bed", "Bed.Level", "Id")]
        f[4] = " ".join(words + BEDS[nid].split() + ["Id=" + nid])
        out[i] = "\t".join(f)
    if out != lines:
        write_text_lines(down, out)
    ups = read_text_lines(up)
    kept = [ln for i, ln in enumerate(ups) if i < H or "_At_Home" not in ln]
    if kept != ups:
        write_text_lines(up, kept)
    print("2,1,0: Edwin and Maren sleep upstairs (their night selves on 2,1,1 gone)")


if __name__ == "__main__":
    stairs()
    edwin_and_maren()
