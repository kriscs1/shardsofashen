"""Every NPC kind has a Level (the owner's wish): the monsters had theirs (build_remnants.py, from their stats); the rest,
townsfolk and animals, get theirs the same way. Each one placed is a little above or below its kind's (world.py
set_npc_level), unless its map line says `Level=`; its health, blows and guard go by it.

  python -I "dev\\migrate\\npc_levels.py"

Safe to run again: a kind that has a Level keeps it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402
from build_remnants import level_of            # noqa: E402


def main():
    ents = Ini(p("data", "Entities.ini"))
    n = 0
    for sec, items in ents.sections:
        if (ents.get(sec, "Type") or "") != "NPC" or ents.get(sec, "Level"):
            continue
        ents.set(sec, "Level", str(level_of(ents, sec)), overwrite=False)
        n += 1
    ents.save(p("data", "Entities.ini"))
    print("Levels given to %d kinds" % n)


if __name__ == "__main__":
    main()
