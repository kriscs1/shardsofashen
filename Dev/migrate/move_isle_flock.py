"""The Isle's sheep and their shepherd (Id=Isle_Shepherd) leave the dairy's yard (2,0,0) for the meadow at the west
of the village (1,1,0), left of the store. A second run does nothing.

  python -I "Dev\\migrate\\move_isle_flock.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_isle import Map, obj_line  # noqa: E402

ZONE = (2, 2, 7, 10)                               # the meadow, in 1,1,0's tiles
SPOTS = [(3, 4), (5, 7), (6, 3), (4, 8)]           # three sheep and the shepherd


def main():
    yard, meadow = Map("2,0,0"), Map("1,1,0")
    if meadow.has_line("Id=Isle_Shepherd"):
        print("The flock is in the meadow already")
        return
    flock = [ln for ln in yard.ents if ln.startswith("NPC\tSheep\t") or "Id=Isle_Shepherd" in ln]
    if not flock:
        print("No flock in the dairy's yard to move")
        return
    zone = "Zone=%d,%d,%d,%d" % ZONE
    for ln, (x, y) in zip(flock, SPOTS * 2):
        p = ln.split("\t")
        opts = " ".join(o if not o.startswith("Zone=") else zone for o in p[4].split())
        meadow.ents.append(obj_line("NPC", p[1], x, y, opts, -8))
    yard.ents = [ln for ln in yard.ents if ln not in flock]
    meadow.save()
    yard.save()
    print("Moved %d (the sheep and the shepherd) to the meadow west of the village" % len(flock))


if __name__ == "__main__":
    main()
