"""Townsfolk climb stairs and ladders: the house stairs (Stairs001 up, Stairs002 down) and ladders (Ladder001 up to a
Hatch001 or a Ladder002) get Climb=1 in Tiles.ini (it was Stairs=1, on the stairs alone), so an NPC whose bed is
upstairs (Bed=x,y Bed.Level=1), whose home is on another level (Home.Level=) or whose Zone is on more than one
(Zone.Levels=0,1) walks to them and up or down (npcs.py npc_to_level, npc_pick_floor_goal). Not a cave's hole
(Ladder006), a tunnel's or a quest's ladder, nor the chapel's stair. Edwin and Maren are one each now, not a day self
downstairs and a night self upstairs:
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
CLIMBS = ("Stairs001", "Stairs002", "Ladder001", "Ladder002", "Hatch001")
H = 21
BEDS = {"Maren_At_Counter": "Bed=13,1 Bed.Level=1",          # (the double bed's left half, and its right)
        "Edwin_At_Desk": "Bed=14,1 Bed.Level=1"}


def climbs():
    lines = read_text_lines(TILES)
    kept = [ln for ln in lines if ln.strip() != "Stairs=1"]          # (the old key: Climb=1 now)
    if kept != lines:
        write_text_lines(TILES, kept)
        ini.forget(TILES)
    n = 0
    for name in CLIMBS:
        if (ini.read(name, "Climb", "", TILES) or "").strip() != "1":
            ini.write(name, "Climb", "1", TILES)
            n += 1
    print("stairs and ladders townsfolk climb: %d marked (%s)" % (n, ", ".join(CLIMBS)))


def edwin_and_maren():
    down, up = os.path.join(ROOT, "maps", "2,1,0.txt"), os.path.join(ROOT, "maps", "2,1,1.txt")
    if not os.path.exists(up):                         # (their house is on 0,-2 now: move_lawyers_house.py)
        print("Edwin and Maren's house has moved (move_lawyers_house.py): nothing to do here.")
        return
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
    climbs()
    edwin_and_maren()
