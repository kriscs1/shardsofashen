"""Passive creatures: a third attitude between Good (can't be attacked) and Bad (a foe). Attitude=Passive can be
attacked but never attacks first: the rabbits, hens, cows, sheep, ducks, otters, seals and frogs (every NPC that was
Bad but never Aggressive). Prey still runs (Flees=1). The page calls them Passive, not Hostile.

Safe to run again.

  python -I "dev\\migrate\\passive_animals.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                      # noqa: E402


def main():
    ents = Ini(p("data", "Entities.ini"))
    n = 0
    for sec, items in ents.sections:
        if (ents.get(sec, "Type") or "") != "NPC" or (ents.get(sec, "Attitude") or "") != "Bad":
            continue
        if sec == "Living_Remnant" or (ents.get(sec, "Aggressive") or "0").strip() not in ("0", ""):
            continue
        ents.set(sec, "Attitude", "Passive")
        n += 1
    ents.save(p("data", "Entities.ini"))
    print("Passive creatures: %d changed" % n)


if __name__ == "__main__":
    main()
